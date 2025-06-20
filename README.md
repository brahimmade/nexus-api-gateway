# Nexus API Gateway

A comprehensive microservice architecture with API Gateway, User Service, Next.js frontend, and monitoring stack using FastAPI, MongoDB, Prometheus, and Grafana.

## Architecture Overview

This project implements a modern microservice architecture with the following components:

- **API Gateway**: FastAPI-based gateway with authentication, rate limiting, and request routing
- **User Service**: User management service with JWT authentication and role-based access control
- **Frontend**: Next.js application with TypeScript and Tailwind CSS
- **Database**: MongoDB with proper indexing and validation
- **Monitoring**: Prometheus metrics collection and Grafana dashboards
- **Message Queue**: Kafka for event-driven communication
- **Containerization**: Docker and Docker Compose for easy deployment

## Features

### API Gateway
- Request routing and load balancing
- JWT-based authentication
- Rate limiting and throttling
- Request/response logging
- Prometheus metrics collection
- Health checks and service discovery
- CORS handling

### User Service
- User registration and authentication
- Role-based access control (RBAC)
- Password hashing with bcrypt
- JWT token management
- User profile management
- Audit logging
- MongoDB integration

### Frontend
- Modern React/Next.js application
- TypeScript for type safety
- Tailwind CSS for styling
- Authentication flows
- Dashboard with real-time metrics
- Responsive design

### Monitoring
- Prometheus metrics collection
- Grafana dashboards
- Health check endpoints
- Performance monitoring
- Error tracking

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Running with Docker

1. Clone the repository:
```bash
git clone https://github.com/brahimmade/nexus-api-gateway.git
cd nexus-api-gateway
```

2. Start all services:
```bash
docker-compose up -d
```

3. Access the applications:
- Frontend: http://localhost:3000
- API Gateway: http://localhost:8000
- User Service: http://localhost:8001
- Grafana: http://localhost:3001 (admin/admin123)
- Prometheus: http://localhost:9090

## API Documentation

### Authentication Endpoints
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login

### User Management Endpoints
- `GET /api/v1/users/me` - Get current user profile
- `GET /api/v1/users` - List all users (admin only)
- `PUT /api/v1/users/{id}` - Update user (admin only)
- `DELETE /api/v1/users/{id}` - Delete user (admin only)

### Health and Monitoring
- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics

## Environment Variables

Key environment variables are configured in the `.env` file:

- `MONGODB_URL` - MongoDB connection string
- `JWT_SECRET` - JWT signing secret
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka server addresses
- `REDIS_URL` - Redis connection string

## Development

### Local Development Setup

1. Install dependencies:
```bash
# Backend
cd backend/api-gateway
pip install -r requirements.txt

cd ../user-service
pip install -r requirements.txt

# Frontend
cd ../../frontend
npm install
```

2. Start services individually:
```bash
# Start MongoDB, Kafka, Redis with Docker
docker-compose up -d mongodb kafka redis

# Start API Gateway
cd backend/api-gateway
uvicorn main:app --reload --port 8000

# Start User Service
cd backend/user-service
uvicorn main:app --reload --port 8001

# Start Frontend
cd frontend
npm run dev
```

## Testing

### Running Tests
```bash
# Backend tests
pytest backend/tests/

# Frontend tests
cd frontend
npm test
```

### API Testing
Use the provided Postman collection or test with curl:

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## Deployment

### Production Deployment

1. Update environment variables for production
2. Use production-ready Docker images
3. Set up proper SSL/TLS certificates
4. Configure load balancers
5. Set up monitoring and alerting

### Security Considerations

- Change default passwords
- Use strong JWT secrets
- Enable HTTPS in production
- Implement proper CORS policies
- Regular security updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue in the GitHub repository.
