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
from api.database.repositories.impersonation_session import ImpersonationSessionRepository
from api.database.repositories.user import UserRepository
from api.middleware.auth import AuthContext, get_auth_context, get_current_admin

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


# Impersonation models
class ImpersonationResponse(BaseModel):
    """Response after starting impersonation."""

    user: UserAdminResponse = Field(..., description="The impersonated user info")
    message: str = Field(..., description="Status message")
    session_id: str = Field(..., description="Impersonation session ID")


class StopImpersonationResponse(BaseModel):
    """Response after stopping impersonation."""

    user: UserAdminResponse = Field(..., description="The admin user info")
    message: str = Field(..., description="Status message")


class ImpersonationStatusResponse(BaseModel):
    """Response with current impersonation status."""

    is_impersonating: bool = Field(..., description="Whether currently impersonating")
    current_user: UserAdminResponse = Field(
        ..., description="Current user (real or impersonated)"
    )
    real_admin: Optional[UserAdminResponse] = Field(
        None, description="Real admin user if impersonating"
    )


@router.post("/impersonate/{user_id}", response_model=ImpersonationResponse)
async def start_impersonation(
    user_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationResponse:
    """
    Start impersonating another user.

    Creates a server-side session that allows the admin to act as the target user.
    All subsequent API calls will return data as if the admin were the target user.

    Requires admin privileges.
    Cannot impersonate yourself or other admins.

    Args:
        user_id: UUID of user to impersonate
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        Impersonated user info and session ID
    """
    try:
        target_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Cannot impersonate yourself
    if target_uuid == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate yourself",
        )

    # Get target user
    user_repo = UserRepository(db)
    data = await user_repo.get_user_with_map_count(target_uuid)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    target_user = data["user"]

    # Cannot impersonate other admins
    if target_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate other administrators",
        )

    # Create impersonation session
    imp_repo = ImpersonationSessionRepository(db)
    session = await imp_repo.create_session(
        admin_id=admin_user.id,
        target_user_id=target_uuid,
    )

    await db.commit()

    logger.info(
        f"Admin {admin_user.email} started impersonating user {target_user.email} "
        f"(session_id={session.id})"
    )

    return ImpersonationResponse(
        user=UserAdminResponse(
            id=str(target_user.id),
            email=target_user.email,
            name=target_user.name,
            avatar_url=target_user.avatar_url,
            is_active=target_user.is_active,
            is_admin=target_user.is_admin,
            created_at=target_user.created_at,
            updated_at=target_user.updated_at,
            last_login_at=target_user.last_login_at,
            map_count=data["map_count"],
        ),
        message=f"Now impersonating {target_user.email}",
        session_id=str(session.id),
    )


@router.post("/stop-impersonation", response_model=StopImpersonationResponse)
async def stop_impersonation(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
) -> StopImpersonationResponse:
    """
    Stop impersonating and return to admin session.

    Deactivates the current impersonation session.
    Only works if currently impersonating.

    Args:
        auth_context: Current auth context with impersonation info
        db: Database session

    Returns:
        Admin user info
    """
    if not auth_context.is_impersonating or not auth_context.real_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not currently impersonating anyone",
        )

    admin_user = auth_context.real_admin
    impersonated_user = auth_context.user

    # Deactivate the session
    if auth_context.impersonation_session_id:
        imp_repo = ImpersonationSessionRepository(db)
        await imp_repo.deactivate_session(UUID(auth_context.impersonation_session_id))
        await db.commit()

    # Get map count for response
    user_repo = UserRepository(db)
    data = await user_repo.get_user_with_map_count(admin_user.id)
    map_count = data["map_count"] if data else 0

    logger.info(
        f"Admin {admin_user.email} stopped impersonating user {impersonated_user.email}"
    )

    return StopImpersonationResponse(
        user=UserAdminResponse(
            id=str(admin_user.id),
            email=admin_user.email,
            name=admin_user.name,
            avatar_url=admin_user.avatar_url,
            is_active=admin_user.is_active,
            is_admin=admin_user.is_admin,
            created_at=admin_user.created_at,
            updated_at=admin_user.updated_at,
            last_login_at=admin_user.last_login_at,
            map_count=map_count,
        ),
        message="Stopped impersonation, back to admin session",
    )


@router.get("/impersonation-status", response_model=ImpersonationStatusResponse)
async def get_impersonation_status(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
) -> ImpersonationStatusResponse:
    """
    Get current impersonation status.

    Returns whether the current session is impersonating another user.

    Args:
        auth_context: Current auth context with impersonation info
        db: Database session

    Returns:
        Current impersonation status
    """
    user = auth_context.user
    user_repo = UserRepository(db)

    # Get map count for current user
    data = await user_repo.get_user_with_map_count(user.id)
    map_count = data["map_count"] if data else 0

    current_user_response = UserAdminResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        map_count=map_count,
    )

    real_admin_response = None
    if auth_context.is_impersonating and auth_context.real_admin:
        admin = auth_context.real_admin
        admin_data = await user_repo.get_user_with_map_count(admin.id)
        admin_map_count = admin_data["map_count"] if admin_data else 0

        real_admin_response = UserAdminResponse(
            id=str(admin.id),
            email=admin.email,
            name=admin.name,
            avatar_url=admin.avatar_url,
            is_active=admin.is_active,
            is_admin=admin.is_admin,
            created_at=admin.created_at,
            updated_at=admin.updated_at,
            last_login_at=admin.last_login_at,
            map_count=admin_map_count,
        )

    return ImpersonationStatusResponse(
        is_impersonating=auth_context.is_impersonating,
        current_user=current_user_response,
        real_admin=real_admin_response,
    )
