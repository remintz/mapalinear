"""
Authentication middleware and dependencies for FastAPI.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.impersonation_session import ImpersonationSessionRepository
from api.services.auth_service import AuthError, AuthService

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """Authentication context with impersonation info."""

    user: User
    is_impersonating: bool = False
    real_admin: Optional[User] = None
    impersonation_session_id: Optional[str] = None


async def _get_auth_context_internal(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
) -> AuthContext:
    """
    Internal function to get authentication context.

    Verifies JWT and checks for active impersonation session.
    """
    auth_service = AuthService(db)

    # Verify JWT and get the authenticated user
    try:
        verify_result = await auth_service.verify_jwt(credentials.credentials)
        authenticated_user = verify_result.user
    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check for active impersonation session
    if authenticated_user.is_admin:
        imp_repo = ImpersonationSessionRepository(db)
        imp_session = await imp_repo.get_active_session_for_admin(authenticated_user.id)

        if imp_session and imp_session.target_user:
            # Admin is impersonating someone
            return AuthContext(
                user=imp_session.target_user,
                is_impersonating=True,
                real_admin=authenticated_user,
                impersonation_session_id=str(imp_session.id),
            )

    # Normal authentication (no impersonation)
    return AuthContext(user=authenticated_user)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Extracts JWT from Authorization header and validates it.
    If an admin has an active impersonation session, returns the impersonated user.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        Authenticated User instance (or impersonated user if impersonating)

    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    context = await _get_auth_context_internal(credentials, db)
    return context.user


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

    try:
        context = await _get_auth_context_internal(credentials, db)
        return context.user
    except HTTPException:
        return None


async def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    FastAPI dependency to get full authentication context including impersonation info.

    Useful for endpoints that need to know if the current session is an impersonation.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        AuthContext with user, impersonation status, and real admin if impersonating

    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await _get_auth_context_internal(credentials, db)


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated admin user.

    Returns the REAL admin user, not the impersonated user.
    This is important for admin endpoints that need the actual admin.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        Authenticated User instance with admin privileges

    Raises:
        HTTPException: If not authenticated or not an admin
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)

    try:
        verify_result = await auth_service.verify_jwt(credentials.credentials)
        user = verify_result.user
    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user


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
