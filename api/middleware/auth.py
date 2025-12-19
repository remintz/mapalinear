"""
Authentication middleware and dependencies for FastAPI.
"""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.services.auth_service import AuthError, AuthService

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Extracts JWT from Authorization header and validates it.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        Authenticated User instance

    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)

    try:
        user = await auth_service.verify_jwt(credentials.credentials)
        return user

    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current user.

    Returns None if no token is provided, but validates if one is.
    Useful for endpoints that work both authenticated and unauthenticated.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User instance or None
    """
    if not credentials:
        return None

    auth_service = AuthService(db)

    try:
        return await auth_service.verify_jwt(credentials.credentials)
    except AuthError:
        return None


def require_auth(request: Request) -> bool:
    """
    Check if the current request requires authentication.

    Used by middleware to determine if auth should be enforced.

    Args:
        request: FastAPI request object

    Returns:
        True if route requires auth, False otherwise
    """
    # Public routes that don't require authentication
    public_paths = [
        "/",
        "/health",
        "/api/auth/google",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    path = request.url.path

    # Check exact matches
    if path in public_paths:
        return False

    # Check prefix matches (e.g., /docs/*)
    for public_path in public_paths:
        if path.startswith(public_path + "/"):
            return False

    return True
