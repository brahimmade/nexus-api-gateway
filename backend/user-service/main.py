from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List
import os
import structlog
from contextlib import asynccontextmanager
import json
from kafka import KafkaProducer
from prometheus_client import Counter, Histogram, generate_latest
from bson import ObjectId
from enum import Enum

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

# Configuration
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://admin:password123@localhost:27017/nexus_db?authSource=admin')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-change-in-production')
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Prometheus metrics
USER_OPERATIONS = Counter('user_service_operations_total', 'Total user operations', ['operation', 'status'])
AUTH_ATTEMPTS = Counter('user_service_auth_attempts_total', 'Authentication attempts', ['status'])

# Global variables
db = None
kafka_producer = None
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"

class Permission(str, Enum):
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"
    MANAGE_ROLES = "manage:roles"
    READ_ANALYTICS = "read:analytics"

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    permissions: List[Permission]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [Permission.READ_USERS, Permission.WRITE_USERS, Permission.DELETE_USERS, 
                     Permission.MANAGE_ROLES, Permission.READ_ANALYTICS],
    UserRole.MODERATOR: [Permission.READ_USERS, Permission.WRITE_USERS, Permission.READ_ANALYTICS],
    UserRole.USER: [Permission.READ_USERS]
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db, kafka_producer
    
    # Initialize MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.nexus_db
    
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")
    
    # Initialize Kafka producer
    try:
        kafka_producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
            value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8')
        )
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.error("Failed to initialize Kafka producer", error=str(e))
    
    logger.info("User service started")
    yield
    
    # Shutdown
    if kafka_producer:
        kafka_producer.close()
    logger.info("User service stopped")

app = FastAPI(
    title="Nexus User Service",
    description="User management service with authentication, authorization, and role-based access control",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_email(email: str):
    user = await db.users.find_one({"email": email})
    return user

async def get_user_by_id(user_id: str):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        return user
    except:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

def require_permission(permission: Permission):
    def permission_checker(current_user: dict = Depends(get_current_user)):
        user_permissions = ROLE_PERMISSIONS.get(current_user["role"], [])
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return permission_checker

def send_user_event(event_type: str, user_data: dict):
    if kafka_producer:
        try:
            event = {
                "event_type": event_type,
                "timestamp": datetime.utcnow(),
                "user_data": user_data
            }
            kafka_producer.send('user_events', event)
        except Exception as e:
            logger.error("Failed to send user event", error=str(e))

# API Endpoints
@app.get("/health")
async def health_check():
    try:
        # Test database connection
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/metrics")
async def metrics():
    return generate_latest()

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    # Check if user already exists
    existing_user = await get_user_by_email(user.email)
    if existing_user:
        USER_OPERATIONS.labels(operation="register", status="failed").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    user_doc = {
        "email": user.email,
        "hashed_password": hashed_password,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
    # Send user creation event
    send_user_event("user_created", {
        "user_id": str(result.inserted_id),
        "email": user.email,
        "role": user.role
    })
    
    USER_OPERATIONS.labels(operation="register", status="success").inc()
    
    return UserResponse(
        id=str(user_doc["_id"]),
        email=user_doc["email"],
        full_name=user_doc["full_name"],
        role=user_doc["role"],
        permissions=ROLE_PERMISSIONS.get(user_doc["role"], []),
        is_active=user_doc["is_active"],
        created_at=user_doc["created_at"]
    )

@app.post("/api/v1/auth/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    user = await get_user_by_email(user_credentials.email)
    if not user or not verify_password(user_credentials.password, user["hashed_password"]):
        AUTH_ATTEMPTS.labels(status="failed").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user["is_active"]:
        AUTH_ATTEMPTS.labels(status="failed").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Update last login
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    
    # Send login event
    send_user_event("user_login", {
        "user_id": str(user["_id"]),
        "email": user["email"]
    })
    
    AUTH_ATTEMPTS.labels(status="success").inc()
    
    user_response = UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        permissions=ROLE_PERMISSIONS.get(user["role"], []),
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=datetime.utcnow()
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user["_id"]),
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        permissions=ROLE_PERMISSIONS.get(current_user["role"], []),
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
        last_login=current_user.get("last_login")
    )

@app.get("/api/v1/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(require_permission(Permission.READ_USERS))
):
    cursor = db.users.find().skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
    return [
        UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            permissions=ROLE_PERMISSIONS.get(user["role"], []),
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user.get("last_login")
        )
        for user in users
    ]

@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(require_permission(Permission.WRITE_USERS))
):
    try:
        user_object_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    result = await db.users.update_one(
        {"_id": user_object_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await get_user_by_id(user_id)
    
    # Send user update event
    send_user_event("user_updated", {
        "user_id": user_id,
        "updated_by": str(current_user["_id"]),
        "changes": update_data
    })
    
    USER_OPERATIONS.labels(operation="update", status="success").inc()
    
    return UserResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        full_name=updated_user["full_name"],
        role=updated_user["role"],
        permissions=ROLE_PERMISSIONS.get(updated_user["role"], []),
        is_active=updated_user["is_active"],
        created_at=updated_user["created_at"],
        last_login=updated_user.get("last_login")
    )

@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_permission(Permission.DELETE_USERS))
):
    try:
        user_object_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Don't allow users to delete themselves
    if str(current_user["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"_id": user_object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Send user deletion event
    send_user_event("user_deleted", {
        "user_id": user_id,
        "deleted_by": str(current_user["_id"])
    })
    
    USER_OPERATIONS.labels(operation="delete", status="success").inc()
    
    return {"message": "User deleted successfully"}

@app.post("/api/v1/users/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    # Verify current password
    if not verify_password(password_change.current_password, current_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    new_hashed_password = get_password_hash(password_change.new_password)
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"hashed_password": new_hashed_password}}
    )
    
    # Send password change event
    send_user_event("password_changed", {
        "user_id": str(current_user["_id"]),
        "email": current_user["email"]
    })
    
    return {"message": "Password changed successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
