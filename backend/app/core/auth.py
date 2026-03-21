"""Authentication and authorization utilities."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

# Password hashing - using pbkdf2_sha256 for better compatibility
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT token scheme
security = HTTPBearer(auto_error=False)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Token(BaseModel):
    """JWT Token response."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """JWT Token payload data."""
    username: Optional[str] = None
    user_id: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model for authentication."""
    username: str
    user_id: str
    email: Optional[str] = None
    is_active: bool = True
    scopes: list[str] = []


# Generate new password hashes
def _generate_test_password_hash() -> str:
    """Generate password hash for 'secret'."""
    return pwd_context.hash("secret")

# DEVELOPMENT-ONLY user store - DO NOT USE IN PRODUCTION
# In production, replace this with a proper database-backed user management system
fake_users_db = {
    "admin": {
        "username": "admin",
        "user_id": "admin-001", 
        "hashed_password": None,  # Will be set dynamically to "dev-password"
        "email": "admin@faro.local",
        "is_active": True,
        "scopes": ["admin", "investigate", "tag", "ingest"]
    },
    "analyst": {
        "username": "analyst", 
        "user_id": "analyst-001",
        "hashed_password": None,  # Will be set dynamically to "dev-password"
        "email": "analyst@faro.local",
        "is_active": True,
        "scopes": ["investigate", "tag"]
    }
}

def _init_password_hashes():
    """
    Initialize password hashes for DEVELOPMENT ONLY.
    
    WARNING: This uses a hardcoded password "dev-password" for all test users.
    In production, this entire authentication system should be replaced with:
    - A proper user database (PostgreSQL, etc.)
    - Secure password requirements and validation
    - User registration/password reset workflows
    - Proper user management interface
    """
    if fake_users_db["admin"]["hashed_password"] is None:
        # DEVELOPMENT ONLY - hardcoded password
        dev_password = "dev-password"  # Make it explicit this is for development
        hash_val = pwd_context.hash(dev_password)
        fake_users_db["admin"]["hashed_password"] = hash_val
        fake_users_db["analyst"]["hashed_password"] = hash_val


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[User]:
    """Get user by username."""
    _init_password_hashes()  # Ensure hashes are initialized
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password."""
    _init_password_hashes()  # Ensure hashes are initialized
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, fake_users_db[username]["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        scopes: list = payload.get("scopes", [])
        
        if username is None:
            return None
        
        token_data = TokenData(username=username, user_id=user_id, scopes=scopes)
        return token_data
    except JWTError:
        return None


def verify_api_key(api_key: str) -> bool:
    """Verify API key for service-to-service authentication."""
    if not settings.api_key:
        return False
    return api_key == settings.api_key


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)] = None,
    api_key: Annotated[str, Depends(api_key_header)] = None,
) -> Optional[User]:
    """Get current authenticated user from JWT token or API key."""
    # Skip authentication if disabled (for development)
    if not settings.auth_enabled:
        return User(username="dev-user", user_id="dev-001", scopes=["admin", "investigate", "tag", "ingest"])
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try API key authentication first
    if api_key:
        if verify_api_key(api_key):
            return User(username="api-service", user_id="api-001", scopes=["admin", "investigate", "tag", "ingest"])
        raise credentials_exception
    
    # Try JWT authentication
    if credentials:
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            raise credentials_exception
        
        user = get_user(username=token_data.username)
        if user is None:
            raise credentials_exception
        
        return user
    
    # No authentication provided
    raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class RequireScopes:
    """Dependency to require specific scopes."""
    
    def __init__(self, *required_scopes: str):
        self.required_scopes = set(required_scopes)
    
    def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        """Check if user has required scopes."""
        user_scopes = set(current_user.scopes)
        
        # Admin scope grants access to everything
        if "admin" in user_scopes:
            return current_user
        
        # Check if user has any of the required scopes
        if not self.required_scopes.intersection(user_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of: {', '.join(self.required_scopes)}"
            )
        
        return current_user


# Common dependencies
RequireInvestigate = RequireScopes("investigate")
RequireTag = RequireScopes("tag")
RequireIngest = RequireScopes("ingest")
RequireAdmin = RequireScopes("admin")