"""
Admin router for user management endpoints.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.user import UserRepository
from api.middleware.auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Response models
class UserAdminResponse(BaseModel):
    """User information for admin views."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    avatar_url: Optional[str] = Field(None, description="URL to user avatar")
    is_active: bool = Field(..., description="Whether user is active")
    is_admin: bool = Field(..., description="Whether user is an administrator")
    created_at: datetime = Field(..., description="When user was created")
    updated_at: datetime = Field(..., description="When user was last updated")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    map_count: int = Field(0, description="Number of maps owned by user")

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Response with list of users."""

    users: List[UserAdminResponse]
    total: int = Field(..., description="Total number of users")


class SetAdminRequest(BaseModel):
    """Request to set admin status."""

    is_admin: bool = Field(..., description="Whether user should be admin")


@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """
    List all users with their statistics.

    Requires admin privileges.

    Args:
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        List of all users with stats
    """
    user_repo = UserRepository(db)
    users_with_stats = await user_repo.get_all_users_with_stats()

    users = [
        UserAdminResponse(
            id=str(data["user"].id),
            email=data["user"].email,
            name=data["user"].name,
            avatar_url=data["user"].avatar_url,
            is_active=data["user"].is_active,
            is_admin=data["user"].is_admin,
            created_at=data["user"].created_at,
            updated_at=data["user"].updated_at,
            last_login_at=data["user"].last_login_at,
            map_count=data["map_count"],
        )
        for data in users_with_stats
    ]

    return UserListResponse(users=users, total=len(users))


@router.get("/users/{user_id}", response_model=UserAdminResponse)
async def get_user(
    user_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    """
    Get a specific user by ID.

    Requires admin privileges.

    Args:
        user_id: UUID of user to get
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        User details with stats
    """
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    user_repo = UserRepository(db)
    data = await user_repo.get_user_with_map_count(uuid)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = data["user"]
    return UserAdminResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        map_count=data["map_count"],
    )


@router.patch("/users/{user_id}/admin", response_model=UserAdminResponse)
async def set_user_admin(
    user_id: str,
    request: SetAdminRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    """
    Set or remove admin status for a user.

    Requires admin privileges.
    Cannot remove admin status from yourself.

    Args:
        user_id: UUID of user to update
        request: Contains new admin status
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        Updated user details
    """
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Prevent admin from removing their own admin status
    if uuid == admin_user.id and not request.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin status from yourself",
        )

    user_repo = UserRepository(db)
    data = await user_repo.get_user_with_map_count(uuid)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = data["user"]
    user = await user_repo.set_admin(user, request.is_admin)

    logger.info(
        f"Admin {admin_user.email} set is_admin={request.is_admin} for user {user.email}"
    )

    return UserAdminResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        map_count=data["map_count"],
    )


@router.patch("/users/{user_id}/active", response_model=UserAdminResponse)
async def set_user_active(
    user_id: str,
    is_active: bool,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    """
    Activate or deactivate a user.

    Requires admin privileges.
    Cannot deactivate yourself.

    Args:
        user_id: UUID of user to update
        is_active: Whether user should be active
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        Updated user details
    """
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Prevent admin from deactivating themselves
    if uuid == admin_user.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    user_repo = UserRepository(db)
    data = await user_repo.get_user_with_map_count(uuid)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = data["user"]
    if is_active:
        user = await user_repo.activate(user)
    else:
        user = await user_repo.deactivate(user)

    logger.info(
        f"Admin {admin_user.email} set is_active={is_active} for user {user.email}"
    )

    return UserAdminResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        map_count=data["map_count"],
    )
