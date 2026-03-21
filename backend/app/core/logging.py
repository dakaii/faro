"""Structured logging configuration for Faro backend."""
import logging
import sys
import os
from typing import Any, Dict

import structlog


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if os.getenv("LOG_LEVEL") != "DEBUG" else logging.DEBUG,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level and timestamp to all log entries
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            # Add correlation ID if available in context
            structlog.contextvars.merge_contextvars,
            # Format for development (human readable) vs production (JSON)
            _get_formatter(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def _get_formatter():
    """Get appropriate log formatter based on environment."""
    if os.getenv("ENVIRONMENT") == "production":
        # JSON formatting for production log aggregation
        return structlog.processors.JSONRenderer()
    else:
        # Human-readable formatting for development
        return structlog.dev.ConsoleRenderer(colors=True)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to all subsequent log entries in this request."""
    for key, value in kwargs.items():
        structlog.contextvars.bind_contextvars(**{key: value})


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


class LoggingMiddleware:
    """Middleware to add request context to logs."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate correlation ID for request tracking
            import uuid
            correlation_id = str(uuid.uuid4())[:8]
            
            # Bind request context
            bind_context(
                correlation_id=correlation_id,
                method=scope.get("method"),
                path=scope.get("path"),
                user_agent=dict(scope.get("headers", {})).get(b"user-agent", b"").decode()
            )
            
            # Log request start
            logger = get_logger("request")
            logger.info(
                "request_started",
                method=scope.get("method"),
                path=scope.get("path")
            )
        
        try:
            await self.app(scope, receive, send)
        finally:
            if scope["type"] == "http":
                # Clear context after request
                clear_context()


# Common log contexts for services
class ServiceLogger:
    """Helper for service-level logging with consistent context."""
    
    def __init__(self, service_name: str):
        self.logger = get_logger(service_name)
        self.service_name = service_name
    
    def info(self, message: str, **kwargs):
        """Log info message with service context."""
        self.logger.info(message, service=self.service_name, **kwargs)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message with service context and error details."""
        error_data = {}
        if error:
            error_data = {
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        
        self.logger.error(
            message, 
            service=self.service_name, 
            **error_data,
            **kwargs
        )
    
    def warning(self, message: str, **kwargs):
        """Log warning message with service context."""
        self.logger.warning(message, service=self.service_name, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with service context."""
        self.logger.debug(message, service=self.service_name, **kwargs)