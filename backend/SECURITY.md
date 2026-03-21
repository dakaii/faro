# Faro Backend Security Guide

## Development vs Production Configuration

### 🔧 Development Setup (Current State)

The current configuration is **DEVELOPMENT ONLY** and includes:

- **Development users**: `admin` and `analyst` with password `dev-password`
- **Development secret key**: Obvious placeholder that triggers validation error
- **Development API key**: Placeholder value
- **Authentication disabled by default** in tests

### 🔐 Production Deployment Checklist

Before deploying to production, **ALL** of the following must be completed:

#### 1. Generate Secure Secrets
```bash
# Generate secure JWT secret key
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate secure API key  
python -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"
```

#### 2. Set Environment Variables
```bash
# Required for production
export SECRET_KEY="your-generated-32-char-secret"
export API_KEY="your-generated-32-char-api-key"
export AUTH_ENABLED="true"
```

#### 3. Replace Mock Authentication System

**CRITICAL**: The current authentication system uses hardcoded users and is for development only.

For production, implement:
- Database-backed user management (PostgreSQL recommended)
- Secure user registration/password reset flows
- Proper password requirements and validation
- User management interface
- Audit logging for security events

#### 4. Security Configuration

**Environment Variables Required:**
```env
# CRITICAL - Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-generated-secret-key-here

# Service-to-service authentication
API_KEY=your-generated-api-key-here

# Enable authentication (should be 'true' in production)
AUTH_ENABLED=true

# Neo4j credentials (change defaults)
NEO4J_PASSWORD=secure-neo4j-password

# Etherscan API
ETHERSCAN_API_KEY=your-etherscan-api-key

# Optional: OpenAI for LLM features
OPENAI_API_KEY=your-openai-api-key
```

#### 5. Container Security

The Docker setup includes:
- ✅ Non-root user (`appuser`)
- ✅ Minimal base image (Python 3.12 slim)
- ✅ Health checks configured
- ✅ Non-conflicting ports (8080, 7475, 7688)

#### 6. Rate Limiting Configuration

Current rate limits:
- **Standard**: 100 requests/hour
- **Strict**: 10 requests/10 minutes  
- **Generous**: 1000 requests/hour

Adjust in `app/middleware/rate_limit.py` based on your needs.

## Authentication & Authorization

### Endpoints

- **POST /auth/login** - JSON login
- **POST /auth/token** - OAuth2 compatible token endpoint
- **GET /auth/me** - Current user information
- **GET /auth/test-auth** - Authentication test

### Scopes

- `admin` - Full access to all endpoints
- `investigate` - Access to wallet investigation
- `tag` - Access to address tagging
- `ingest` - Access to document ingestion

### Authentication Methods

1. **JWT Tokens**
   - Bearer token in Authorization header
   - Configurable expiration (default: 30 minutes)
   
2. **API Keys**
   - X-API-Key header for service-to-service calls
   - Full admin access when valid

## Security Features Implemented

### ✅ Current Security Controls

- **JWT Authentication** with proper token validation
- **Role-based authorization** with scopes
- **Rate limiting** with in-memory storage
- **Input validation** for wallet addresses and API parameters
- **CORS configuration** with configurable origins
- **Password hashing** using PBKDF2-SHA256
- **Non-root container** user for Docker security
- **Environment variable** configuration for secrets

### 🔄 Planned Security Improvements

- **Audit logging** for security events
- **Token invalidation** (logout functionality)
- **Database-backed user management**
- **Session management** improvements
- **Security headers** enhancement
- **File upload security** scanning

## Monitoring & Alerting

### Logs to Monitor

Currently basic FastAPI logs. Add monitoring for:
- Failed authentication attempts
- Rate limit violations
- Invalid API requests
- Security events

### Recommended Tools

- **Application logs**: Structured JSON logging
- **Monitoring**: Prometheus + Grafana
- **Alerting**: Based on failed auth attempts
- **Security**: OWASP security headers

## Incident Response

### Common Security Issues

1. **Brute force attacks**: Monitor failed login attempts
2. **Rate limit abuse**: Check rate limiter logs  
3. **Invalid tokens**: JWT validation failures
4. **Unauthorized access**: Scope validation failures

### Response Actions

1. Review logs for attack patterns
2. Temporarily increase rate limits if needed
3. Revoke compromised tokens (when logout is implemented)
4. Update security configurations as needed

## Development vs Production Differences

| Aspect | Development | Production |
|--------|-------------|------------|
| Authentication | Optional (`AUTH_ENABLED=false` in tests) | Required |
| Users | Hardcoded admin/analyst | Database-backed |
| Passwords | `dev-password` | Secure requirements |
| Secrets | Placeholder values | Generated secure keys |
| Rate Limiting | Disabled in tests | Enabled |
| Logging | Basic | Structured + audit |

## Security Validation

Before production deployment, verify:

```bash
# 1. Secret key validation
python -c "
from app.core.config import settings
try:
    settings.validate_production_settings()
    print('✅ Security configuration valid')
except ValueError as e:
    print(f'❌ Security error: {e}')
"

# 2. Authentication test
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "dev-password"}'

# 3. Rate limiting test  
for i in {1..5}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/health
done
```

## Contact & Support

For security issues or questions:
- Review this document first
- Check application logs
- Consult FastAPI security documentation
- Consider professional security audit for production