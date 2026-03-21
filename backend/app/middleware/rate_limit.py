"""Rate limiting middleware."""
import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for development."""
    
    def __init__(self):
        # Store: {client_id: [(timestamp, count), ...]}
        self.storage: Dict[str, list[Tuple[float, int]]] = {}
        self.cleanup_interval = 300  # Clean up old entries every 5 minutes
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit."""
        now = time.time()
        
        # Periodic cleanup
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(now)
            self.last_cleanup = now
        
        # Initialize if not exists
        if key not in self.storage:
            self.storage[key] = []
        
        # Remove old entries outside the window
        window_start = now - window
        self.storage[key] = [
            (timestamp, count) 
            for timestamp, count in self.storage[key] 
            if timestamp > window_start
        ]
        
        # Count current requests in window
        current_count = sum(count for _, count in self.storage[key])
        
        if current_count >= limit:
            return False
        
        # Add current request
        self.storage[key].append((now, 1))
        return True
    
    def _cleanup_old_entries(self, now: float):
        """Remove very old entries to prevent memory leaks."""
        cutoff = now - 3600  # Remove entries older than 1 hour
        for key in list(self.storage.keys()):
            self.storage[key] = [
                (timestamp, count) 
                for timestamp, count in self.storage[key] 
                if timestamp > cutoff
            ]
            if not self.storage[key]:
                del self.storage[key]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()

# SlowAPI limiter for decorator-based rate limiting
limiter = Limiter(key_func=get_remote_address)


def get_client_identifier(request: Request) -> str:
    """Get client identifier for rate limiting."""
    # Try to get authenticated user ID first
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.user_id}"
    
    # Fall back to IP address
    client_ip = get_remote_address(request)
    return f"ip:{client_ip}"


def check_rate_limit(request: Request, limit: int = 100, window: int = 3600) -> bool:
    """
    Check rate limit for a request.
    
    Args:
        request: FastAPI request object
        limit: Maximum requests allowed
        window: Time window in seconds
        
    Returns:
        True if request is allowed, raises HTTPException if not
    """
    client_id = get_client_identifier(request)
    
    if not rate_limiter.is_allowed(client_id, limit, window):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(window)}
        )
    
    return True


def rate_limit_dependency(limit: int = 100, window: int = 3600):
    """
    Create a FastAPI dependency for rate limiting.
    
    Args:
        limit: Maximum requests allowed
        window: Time window in seconds
        
    Usage:
        @app.get("/api/endpoint")
        async def endpoint(rate_limit: bool = Depends(rate_limit_dependency(10, 60))):
            # This endpoint allows 10 requests per minute
            pass
    """
    def dependency(request: Request) -> bool:
        return check_rate_limit(request, limit, window)
    
    return dependency


# Pre-configured rate limit dependencies
standard_rate_limit = rate_limit_dependency(100, 3600)  # 100 per hour
strict_rate_limit = rate_limit_dependency(10, 600)  # 10 per 10 minutes
generous_rate_limit = rate_limit_dependency(1000, 3600)  # 1000 per hour


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler."""
    response = HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Rate limit exceeded: {exc.detail}",
        headers={"Retry-After": "60"}
    )
    return response