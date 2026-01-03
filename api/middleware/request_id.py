"""
Request ID middleware for tracking requests and async operations.

Generates a short hexadecimal ID (8 characters) for each request or
async operation, making it easy to filter logs by request/process.
"""

import logging
import os
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context variable to store the current request/process ID
_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a random 8-character hexadecimal ID."""
    return os.urandom(4).hex()


def get_request_id() -> Optional[str]:
    """Get the current request/process ID."""
    return _request_id_ctx.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set the current request/process ID.

    Args:
        request_id: Optional ID to set. If None, generates a new one.

    Returns:
        The request ID that was set.
    """
    if request_id is None:
        request_id = generate_request_id()
    _request_id_ctx.set(request_id)
    return request_id


def clear_request_id() -> None:
    """Clear the current request/process ID."""
    _request_id_ctx.set(None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique ID to each HTTP request."""

    async def dispatch(self, request: Request, call_next):
        # Generate and set request ID
        request_id = set_request_id()

        # Add to request state for access in routes if needed
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_request_id()


class RequestIDFilter(logging.Filter):
    """
    Logging filter that adds request_id to log records.

    This filter adds a 'request_id' attribute to each log record,
    which can be used in log formatters.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = get_request_id()
        record.request_id = request_id if request_id else "--------"
        return True
