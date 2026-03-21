"""Authentication endpoints."""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.auth import (
    Token, User, authenticate_user, create_access_token, get_current_active_user
)
from app.core.config import settings

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""
    username: str
    user_id: str
    email: str | None = None
    is_active: bool
    scopes: list[str]


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    Use this endpoint to authenticate and get a JWT token.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.user_id,
            "scopes": user.scopes
        },
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest) -> Token:
    """
    Alternative login endpoint that accepts JSON.
    
    Use this for programmatic access or when OAuth2 form is not suitable.
    """
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.user_id,
            "scopes": user.scopes
        },
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> UserResponse:
    """
    Get current user information.
    
    Returns information about the currently authenticated user.
    """
    return UserResponse(**current_user.model_dump())


@router.get("/test-auth")
async def test_auth(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """Test endpoint to verify authentication is working."""
    return {
        "message": f"Hello {current_user.username}!",
        "user_id": current_user.user_id,
        "scopes": current_user.scopes,
        "auth_status": "success"
    }