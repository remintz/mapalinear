"""
Admin router for user management endpoints.
"""

import logging
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
from api.models.base import UTCDatetime

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
    created_at: UTCDatetime = Field(..., description="When user was created")
    updated_at: UTCDatetime = Field(..., description="When user was last updated")
    last_login_at: Optional[UTCDatetime] = Field(None, description="Last login timestamp")
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


# Map admin models
class MapAdminResponse(BaseModel):
    """Map information for admin views."""

    id: str = Field(..., description="Map UUID")
    origin: str = Field(..., description="Origin location")
    destination: str = Field(..., description="Destination location")
    total_length_km: float = Field(..., description="Total route length in km")
    created_at: UTCDatetime = Field(..., description="When map was created")
    updated_at: UTCDatetime = Field(..., description="When map was last updated")
    user_count: int = Field(0, description="Number of users with this map")
    created_by_user_id: Optional[str] = Field(None, description="Creator user ID")

    model_config = {"from_attributes": True}


class MapListResponse(BaseModel):
    """Response with list of maps."""

    maps: List[MapAdminResponse]
    total: int = Field(..., description="Total number of maps")


class MapDetailResponse(MapAdminResponse):
    """Detailed map information for admin views."""

    poi_counts: dict = Field(default_factory=dict, description="POI counts by category")


@router.get("/maps", response_model=MapListResponse)
async def list_maps(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> MapListResponse:
    """
    List all maps with their user counts.

    Requires admin privileges.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        List of all maps with stats
    """
    from api.database.repositories.map import MapRepository

    map_repo = MapRepository(db)
    maps_with_counts = await map_repo.get_all_maps_with_user_count(skip=skip, limit=limit)
    total = await map_repo.count_all_maps()

    maps = [
        MapAdminResponse(
            id=str(data["map"].id),
            origin=data["map"].origin,
            destination=data["map"].destination,
            total_length_km=data["map"].total_length_km,
            created_at=data["map"].created_at,
            updated_at=data["map"].updated_at,
            user_count=data["user_count"],
            created_by_user_id=str(data["map"].created_by_user_id) if data["map"].created_by_user_id else None,
        )
        for data in maps_with_counts
    ]

    return MapListResponse(maps=maps, total=total)


@router.get("/maps/{map_id}", response_model=MapDetailResponse)
async def get_map_details(
    map_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> MapDetailResponse:
    """
    Get detailed information about a specific map.

    Requires admin privileges.

    Args:
        map_id: UUID of map to get
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        Detailed map information including POI counts by category
    """
    from collections import Counter

    from sqlalchemy.orm import selectinload

    from api.database.models.map import Map
    from api.database.models.map_poi import MapPOI
    from api.database.models.poi import POI
    from api.database.repositories.map import MapRepository
    from api.database.repositories.user_map import UserMapRepository

    try:
        uuid = UUID(map_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid map ID format",
        )

    map_repo = MapRepository(db)
    map_obj = await map_repo.get_by_id_with_pois(uuid)

    if not map_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Map not found",
        )

    # Count POIs by type
    poi_counts: dict = Counter()
    for map_poi in map_obj.map_pois:
        if map_poi.poi:
            poi_counts[map_poi.poi.type] += 1

    user_map_repo = UserMapRepository(db)
    user_count = await user_map_repo.get_map_user_count(uuid)

    return MapDetailResponse(
        id=str(map_obj.id),
        origin=map_obj.origin,
        destination=map_obj.destination,
        total_length_km=map_obj.total_length_km,
        created_at=map_obj.created_at,
        updated_at=map_obj.updated_at,
        user_count=user_count,
        created_by_user_id=str(map_obj.created_by_user_id) if map_obj.created_by_user_id else None,
        poi_counts=dict(poi_counts),
    )


# Database maintenance models
class DatabaseStatsResponse(BaseModel):
    """Current database statistics."""

    total_pois: int = Field(..., description="Total number of POIs")
    referenced_pois: int = Field(..., description="POIs referenced by maps")
    unreferenced_pois: int = Field(..., description="Orphan POIs not in any map")
    total_maps: int = Field(..., description="Total number of maps")
    total_map_pois: int = Field(..., description="Total map-POI relationships")
    total_segments: int = Field(0, description="Total number of route segments")
    orphan_segments: int = Field(0, description="Orphan segments not used by any map")
    pending_operations: int = Field(..., description="Operations in progress")
    stale_operations: int = Field(..., description="Stale operations (>2h)")


class MaintenanceResultResponse(BaseModel):
    """Result of a maintenance operation."""

    orphan_pois_found: int = Field(..., description="Number of orphan POIs found")
    orphan_pois_deleted: int = Field(..., description="Number of orphan POIs deleted")
    orphan_segments_found: int = Field(0, description="Number of orphan segments found")
    orphan_segments_deleted: int = Field(0, description="Number of orphan segments deleted")
    is_referenced_fixed: int = Field(..., description="Number of is_referenced flags fixed")
    stale_operations_cleaned: int = Field(..., description="Number of stale operations cleaned")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    dry_run: bool = Field(..., description="Whether this was a dry run")


@router.get("/maintenance/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DatabaseStatsResponse:
    """
    Get current database statistics.

    Shows counts of POIs, maps, and identifies potential issues like orphan POIs.

    Requires admin privileges.

    Args:
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        Database statistics
    """
    from api.services.database_maintenance_service import DatabaseMaintenanceService

    service = DatabaseMaintenanceService(db)
    stats = await service.get_database_stats()

    return DatabaseStatsResponse(
        total_pois=stats.total_pois,
        referenced_pois=stats.referenced_pois,
        unreferenced_pois=stats.unreferenced_pois,
        total_maps=stats.total_maps,
        total_map_pois=stats.total_map_pois,
        total_segments=stats.total_segments,
        orphan_segments=stats.orphan_segments,
        pending_operations=stats.pending_operations,
        stale_operations=stats.stale_operations,
    )


@router.post("/maintenance/run", response_model=MaintenanceResultResponse)
async def run_maintenance(
    dry_run: bool = True,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResultResponse:
    """
    Run database maintenance tasks.

    This will:
    - Delete orphan POIs (POIs not referenced by any map)
    - Fix incorrect is_referenced flags
    - Clean up stale async operations

    Requires admin privileges.

    Args:
        dry_run: If True, only report what would be done without making changes
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        Maintenance results
    """
    from api.services.database_maintenance_service import DatabaseMaintenanceService

    logger.info(
        f"Admin {admin_user.email} initiated database maintenance (dry_run={dry_run})"
    )

    service = DatabaseMaintenanceService(db)
    stats = await service.run_full_maintenance(dry_run=dry_run)

    return MaintenanceResultResponse(
        orphan_pois_found=stats.orphan_pois_found,
        orphan_pois_deleted=stats.orphan_pois_deleted,
        orphan_segments_found=stats.orphan_segments_found,
        orphan_segments_deleted=stats.orphan_segments_deleted,
        is_referenced_fixed=stats.is_referenced_fixed,
        stale_operations_cleaned=stats.stale_operations_cleaned,
        execution_time_ms=stats.execution_time_ms,
        dry_run=dry_run,
    )


# Log cleanup models
class LogCleanupResultResponse(BaseModel):
    """Result of log cleanup operation."""

    retention_days: int = Field(..., description="Configured retention period in days")
    cutoff_date: str = Field(..., description="Logs before this date were deleted")
    application_logs_deleted: int = Field(..., description="Application logs deleted")
    api_logs_deleted: int = Field(..., description="API call logs deleted")
    frontend_logs_deleted: int = Field(..., description="Frontend error logs deleted")
    total_deleted: int = Field(..., description="Total logs deleted")


@router.post("/maintenance/cleanup-logs", response_model=LogCleanupResultResponse)
async def cleanup_logs(
    admin_user: User = Depends(get_current_admin),
) -> LogCleanupResultResponse:
    """
    Manually run log cleanup.

    Deletes logs older than the configured retention period.
    This is the same cleanup that runs automatically every 24 hours.

    Requires admin privileges.

    Args:
        admin_user: Current admin user (injected)

    Returns:
        Cleanup statistics
    """
    from api.services.log_cleanup_service import get_log_cleanup_service

    logger.info(f"Admin {admin_user.email} initiated manual log cleanup")

    service = get_log_cleanup_service()
    result = await service.run_manual_cleanup()

    logger.info(
        f"Manual log cleanup completed: {result['total_deleted']} logs deleted "
        f"(retention: {result['retention_days']} days)"
    )

    return LogCleanupResultResponse(
        retention_days=result["retention_days"],
        cutoff_date=result["cutoff_date"],
        application_logs_deleted=result["application_logs_deleted"],
        api_logs_deleted=result["api_logs_deleted"],
        frontend_logs_deleted=result["frontend_logs_deleted"],
        total_deleted=result["total_deleted"],
    )


# Async Operations Admin models
class OperationUserResponse(BaseModel):
    """User info for operation responses."""

    id: str
    email: str
    name: str

    model_config = {"from_attributes": True}


class AdminOperationResponse(BaseModel):
    """Async operation information for admin views."""

    id: str = Field(..., description="Operation UUID")
    operation_type: str = Field(..., description="Type of operation")
    status: str = Field(..., description="Status: in_progress, completed, failed")
    progress_percent: float = Field(..., description="Progress 0-100")
    started_at: UTCDatetime = Field(..., description="When operation started")
    completed_at: Optional[UTCDatetime] = Field(None, description="When operation completed")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    user: Optional[OperationUserResponse] = Field(None, description="User who requested")
    # Map info extracted from result
    origin: Optional[str] = Field(None, description="Origin location")
    destination: Optional[str] = Field(None, description="Destination location")
    total_length_km: Optional[float] = Field(None, description="Route length in km")

    model_config = {"from_attributes": True}


class AdminOperationListResponse(BaseModel):
    """Response with list of operations."""

    operations: List[AdminOperationResponse]
    total: int = Field(..., description="Total number of operations")
    stats: dict = Field(default_factory=dict, description="Operation statistics")


class CancelOperationResponse(BaseModel):
    """Response after cancelling an operation."""

    success: bool
    message: str


@router.post("/operations/{operation_id}/cancel", response_model=CancelOperationResponse)
async def cancel_operation(
    operation_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> CancelOperationResponse:
    """
    Cancel an in-progress operation.

    Marks the operation as failed. Useful for cleaning up stuck operations.

    Requires admin privileges.

    Args:
        operation_id: UUID of the operation to cancel
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        Success status and message
    """
    from api.database.repositories.async_operation import AsyncOperationRepository

    repo = AsyncOperationRepository(db)
    operation = await repo.get_by_operation_id(operation_id)

    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found",
        )

    if operation.status != "in_progress":
        return CancelOperationResponse(
            success=False,
            message=f"Operação não pode ser cancelada (status: {operation.status})",
        )

    success = await repo.fail_operation(
        operation_id=operation_id,
        error="Operação cancelada pelo administrador",
    )

    if success:
        logger.info(f"Admin {admin_user.email} cancelled operation {operation_id}")
        return CancelOperationResponse(
            success=True,
            message="Operação cancelada com sucesso",
        )
    else:
        return CancelOperationResponse(
            success=False,
            message="Erro ao cancelar operação",
        )


@router.get("/operations", response_model=AdminOperationListResponse)
async def list_operations(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminOperationListResponse:
    """
    List all async operations with details.

    Requires admin privileges.

    Args:
        status: Filter by status (in_progress, completed, failed)
        skip: Number of records to skip
        limit: Maximum number of records to return
        admin_user: Current admin user (injected)
        db: Database session

    Returns:
        List of operations with user info and statistics
    """
    from api.database.repositories.async_operation import AsyncOperationRepository

    repo = AsyncOperationRepository(db)

    # Get operations with user info (all map-related operations)
    operations = await repo.list_all_operations(
        status=status,
        skip=skip,
        limit=limit,
    )

    # Get total count
    total = await repo.count_operations(
        status=status,
    )

    # Get stats
    stats = await repo.get_stats()

    # Convert to response models
    operation_responses = []
    for op in operations:
        # Calculate duration
        duration = None
        if op.completed_at and op.started_at:
            duration = (op.completed_at - op.started_at).total_seconds()

        # Extract map info from result
        origin = None
        destination = None
        total_length_km = None
        if op.result:
            origin = op.result.get("origin")
            destination = op.result.get("destination")
            total_length_km = op.result.get("total_length_km")

        # Build user response
        user_response = None
        if op.user:
            user_response = OperationUserResponse(
                id=str(op.user.id),
                email=op.user.email,
                name=op.user.name,
            )

        operation_responses.append(
            AdminOperationResponse(
                id=op.id,
                operation_type=op.operation_type,
                status=op.status,
                progress_percent=op.progress_percent,
                started_at=op.started_at,
                completed_at=op.completed_at,
                duration_seconds=duration,
                error=op.error,
                user=user_response,
                origin=origin,
                destination=destination,
                total_length_km=total_length_km,
            )
        )

    return AdminOperationListResponse(
        operations=operation_responses,
        total=total,
        stats=stats,
    )
