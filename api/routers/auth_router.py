"""
Authentication router for Google OAuth endpoints.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.middleware.auth import get_current_user
from api.services.auth_service import AuthError, AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response models
class GoogleAuthRequest(BaseModel):
    """Request body for Google OAuth authentication."""

    token: str = Field(..., description="Google ID token from frontend")


class AuthResponse(BaseModel):
    """Response after successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: "UserResponse" = Field(..., description="Authenticated user info")


class UserResponse(BaseModel):
    """User information response."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    avatar_url: Optional[str] = Field(None, description="URL to user avatar")
    is_admin: bool = Field(False, description="Whether user is an administrator")

    model_config = {"from_attributes": True}


# Update forward reference
AuthResponse.model_rebuild()


@router.post("/google", response_model=AuthResponse)
async def authenticate_with_google(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Authenticate with Google OAuth.

    Receives a Google ID token from the frontend, verifies it with Google,
    creates or updates the user in the database, and returns a JWT.

    Args:
        request: Contains the Google ID token
        db: Database session

    Returns:
        AuthResponse with JWT and user info

    Raises:
        HTTPException: If authentication fails
    """
    auth_service = AuthService(db)

    try:
        user, jwt_token = await auth_service.authenticate_with_google(request.token)

        return AuthResponse(
            access_token=jwt_token,
            token_type="bearer",
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                is_admin=user.is_admin,
            ),
        )

    except AuthError as e:
        logger.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current authenticated user information.

    Requires a valid JWT in the Authorization header.

    Args:
        current_user: Injected by auth dependency

    Returns:
        Current user information
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        is_admin=current_user.is_admin,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Logout the current user.

    Note: Since we use stateless JWTs, this endpoint doesn't actually
    invalidate the token. The frontend should discard the token.
    In a production system, you might want to implement token blacklisting.

    Args:
        current_user: Injected by auth dependency
    """
    logger.info(f"User logged out: {current_user.email}")
    # Token invalidation would go here if implemented
    return None
