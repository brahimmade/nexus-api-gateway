from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import httpx
import os
import time
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from contextlib import asynccontextmanager
from typing import Optional
import json
from kafka import KafkaProducer
from jose import JWTError, jwt

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('api_gateway_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_gateway_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
SERVICE_HEALTH = Counter('api_gateway_service_health_total', 'Service health checks', ['service', 'status'])

# Configuration
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:8001')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-change-in-production')
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
ALGORITHM = "HS256"

# Global variables
kafka_producer = None
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global kafka_producer
    try:
        kafka_producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.error("Failed to initialize Kafka producer", error=str(e))
    
    yield
    
    # Shutdown
    if kafka_producer:
        kafka_producer.close()
        logger.info("Kafka producer closed")

app = FastAPI(
    title="Nexus API Gateway",
    description="A powerful and scalable API gateway for microservices",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request logging and metrics
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host
    )
    
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    # Log response
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration=duration
    )
    
    # Send event to Kafka
    if kafka_producer:
        try:
            event = {
                "timestamp": time.time(),
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "duration": duration,
                "client_ip": request.client.host
            }
            kafka_producer.send('api_gateway_events', event)
        except Exception as e:
            logger.error("Failed to send event to Kafka", error=str(e))
    
    return response

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return {"user_id": user_id, "token": credentials.credentials}
    except JWTError:
        return None

# Service proxy function
async def proxy_request(service_url: str, path: str, method: str, headers: dict, body: bytes = None):
    url = f"{service_url}{path}"
    
    # Remove host header to avoid conflicts
    headers.pop('host', None)
    
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, content=body)
            elif method == "PUT":
                response = await client.put(url, headers=headers, content=body)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, content=body)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            return JSONResponse(
                content=response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except httpx.RequestError as e:
            logger.error(f"Service request failed", service_url=service_url, error=str(e))
            raise HTTPException(status_code=503, detail="Service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error", service_url=service_url, error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@app.get("/health")
async def health_check():
    health_status = {"status": "healthy", "services": {}}
    
    # Check user service health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{USER_SERVICE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                health_status["services"]["user_service"] = "healthy"
                SERVICE_HEALTH.labels(service="user_service", status="healthy").inc()
            else:
                health_status["services"]["user_service"] = "unhealthy"
                SERVICE_HEALTH.labels(service="user_service", status="unhealthy").inc()
    except Exception:
        health_status["services"]["user_service"] = "unhealthy"
        SERVICE_HEALTH.labels(service="user_service", status="unhealthy").inc()
    
    # Overall health
    if any(status == "unhealthy" for status in health_status["services"].values()):
        health_status["status"] = "degraded"
    
    return health_status

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return generate_latest()

# API Gateway info
@app.get("/")
async def root():
    return {
        "service": "Nexus API Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "user_service": "/api/v1/users/*",
            "auth": "/api/v1/auth/*"
        }
    }

# User service routes (with authentication)
@app.api_route("/api/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def user_service_proxy(
    request: Request,
    path: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    # Public endpoints that don't require authentication
    public_endpoints = ["/register", "/login", "/health"]
    
    if not any(path.startswith(endpoint.lstrip('/')) for endpoint in public_endpoints) and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    headers = dict(request.headers)
    if current_user:
        headers["X-User-ID"] = current_user["user_id"]
        headers["Authorization"] = f"Bearer {current_user['token']}"
    
    body = await request.body()
    return await proxy_request(USER_SERVICE_URL, f"/api/v1/users/{path}", request.method, headers, body)

# Authentication routes (public)
@app.api_route("/api/v1/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def auth_service_proxy(request: Request, path: str):
    headers = dict(request.headers)
    body = await request.body()
    return await proxy_request(USER_SERVICE_URL, f"/api/v1/auth/{path}", request.method, headers, body)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
