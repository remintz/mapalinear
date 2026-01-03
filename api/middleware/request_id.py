"""
Request ID and Session ID middleware for tracking requests and async operations.

Generates a short hexadecimal ID (8 characters) for each request or
async operation, making it easy to filter logs by request/process.

Also captures the frontend session ID from X-Session-ID header for
correlating frontend errors with backend logs.
"""

import logging
import os
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context variable to store the current request/process ID
_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Context variable to store the frontend session ID
_session_id_ctx: ContextVar[Optional[str]] = ContextVar("session_id", default=None)

# Context variable to store the authenticated user email
_user_email_ctx: ContextVar[Optional[str]] = ContextVar("user_email", default=None)


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


def get_session_id() -> Optional[str]:
    """Get the current frontend session ID."""
    return _session_id_ctx.get()


def set_session_id(session_id: Optional[str]) -> Optional[str]:
    """
    Set the current frontend session ID.

    Args:
        session_id: The session ID from the X-Session-ID header.

    Returns:
        The session ID that was set.
    """
    _session_id_ctx.set(session_id)
    return session_id


def clear_session_id() -> None:
    """Clear the current frontend session ID."""
    _session_id_ctx.set(None)


def get_user_email() -> Optional[str]:
    """Get the current authenticated user email."""
    return _user_email_ctx.get()


def set_user_email(user_email: Optional[str]) -> Optional[str]:
    """
    Set the current authenticated user email.

    Args:
        user_email: The user email from authenticated session.

    Returns:
        The user email that was set.
    """
    _user_email_ctx.set(user_email)
    return user_email


def clear_user_email() -> None:
    """Clear the current authenticated user email."""
    _user_email_ctx.set(None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique ID to each HTTP request and captures session ID."""

    async def dispatch(self, request: Request, call_next):
        # Generate and set request ID
        request_id = set_request_id()

        # Capture session ID from frontend header
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            set_session_id(session_id)

        # Add to request state for access in routes if needed
        request.state.request_id = request_id
        request.state.session_id = session_id

        try:
            response = await call_next(request)
            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_request_id()
            clear_session_id()
            clear_user_email()


class RequestIDFilter(logging.Filter):
    """
    Logging filter that adds request_id, session_id, and user_email to log records.

    This filter adds 'request_id', 'session_id', and 'user_email' attributes to each
    log record, which can be used in log formatters.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = get_request_id()
        session_id = get_session_id()
        user_email = get_user_email()
        record.request_id = request_id if request_id else "--------"
        # Use first 8 chars of session_id for brevity in logs
        record.session_id = session_id[:8] if session_id else "--------"
        # Add user_email
        record.user_email = user_email
        return True
