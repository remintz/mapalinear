"""
Router for GPS debug logs endpoints.

Provides endpoints for receiving and viewing GPS debug data
reported by admin users during real-world testing.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.repositories.gps_debug_log import GPSDebugLogRepository
from api.middleware.auth import get_current_admin
from api.models.base import UTCDatetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gps-debug", tags=["GPS Debug"])


# Throttle time in minutes
THROTTLE_MINUTES = 5


# Request/Response Models


class POIInfo(BaseModel):
    """POI information in debug log."""

    id: str
    name: str
    type: str
    distance_from_origin_km: float
    relative_distance_km: float = Field(
        description="Distance relative to user position (negative = passed, positive = ahead)"
    )


class GPSDebugLogRequest(BaseModel):
    """Request body for creating a GPS debug log."""

    map_id: str = Field(..., description="Map ID being viewed")
    map_origin: str = Field(..., description="Map origin city")
    map_destination: str = Field(..., description="Map destination city")
    latitude: float = Field(..., description="GPS latitude")
    longitude: float = Field(..., description="GPS longitude")
    gps_accuracy: Optional[float] = Field(None, description="GPS accuracy in meters")
    distance_from_origin_km: Optional[float] = Field(
        None, description="Calculated distance from route origin"
    )
    is_on_route: bool = Field(False, description="Whether user is on route")
    distance_to_route_m: Optional[float] = Field(
        None, description="Distance to nearest point on route in meters"
    )
    previous_pois: Optional[List[POIInfo]] = Field(
        None, description="2 POIs before current position"
    )
    next_pois: Optional[List[POIInfo]] = Field(
        None, description="5 POIs after current position"
    )
    session_id: Optional[str] = Field(None, description="Frontend session ID")


class GPSDebugLogResponse(BaseModel):
    """Response for a single GPS debug log."""

    id: str
    created_at: UTCDatetime
    user_email: str
    map_id: str
    map_origin: str
    map_destination: str
    latitude: float
    longitude: float
    gps_accuracy: Optional[float]
    distance_from_origin_km: Optional[float]
    is_on_route: bool
    distance_to_route_m: Optional[float]
    previous_pois: Optional[List[dict]]
    next_pois: Optional[List[dict]]
    session_id: Optional[str]


# Endpoints


@router.post("", status_code=201)
async def create_gps_debug_log(
    log_data: GPSDebugLogRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    Create a GPS debug log entry.

    This endpoint requires admin authentication.
    Logs are throttled to max 1 per 5 minutes per user/map combination.
    """
    repo = GPSDebugLogRepository(db)

    user_id = current_user["id"]
    user_email = current_user["email"]

    # Check throttle - don't log if last log was less than 5 minutes ago
    last_log = await repo.get_last_log_for_user_map(user_id, log_data.map_id)
    if last_log:
        time_since_last = datetime.now(last_log.created_at.tzinfo) - last_log.created_at
        if time_since_last < timedelta(minutes=THROTTLE_MINUTES):
            remaining = THROTTLE_MINUTES - (time_since_last.total_seconds() / 60)
            return {
                "status": "throttled",
                "message": f"Log throttled. Next log allowed in {remaining:.1f} minutes.",
                "last_log_at": last_log.created_at.isoformat(),
            }

    # Extract user agent from request headers
    user_agent = request.headers.get("user-agent", "unknown")[:500]

    # Convert POI info to dict for storage
    previous_pois_data = None
    if log_data.previous_pois:
        previous_pois_data = [poi.model_dump() for poi in log_data.previous_pois]

    next_pois_data = None
    if log_data.next_pois:
        next_pois_data = [poi.model_dump() for poi in log_data.next_pois]

    # Create the log
    log = await repo.create_log(
        user_id=user_id,
        user_email=user_email,
        map_id=log_data.map_id,
        map_origin=log_data.map_origin,
        map_destination=log_data.map_destination,
        latitude=log_data.latitude,
        longitude=log_data.longitude,
        gps_accuracy=log_data.gps_accuracy,
        distance_from_origin_km=log_data.distance_from_origin_km,
        is_on_route=log_data.is_on_route,
        distance_to_route_m=log_data.distance_to_route_m,
        previous_pois=previous_pois_data,
        next_pois=next_pois_data,
        session_id=log_data.session_id,
        user_agent=user_agent,
    )

    await db.commit()

    logger.info(
        f"[GPS DEBUG] Admin {user_email} logged position: "
        f"lat={log_data.latitude:.5f}, lon={log_data.longitude:.5f}, "
        f"distance={log_data.distance_from_origin_km:.2f}km, "
        f"map={log_data.map_id[:8]}..."
    )

    return {
        "status": "ok",
        "message": "GPS debug log created successfully",
        "log_id": str(log.id),
    }


@router.get("/recent", response_model=List[GPSDebugLogResponse])
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    """
    Get recent GPS debug logs.

    Requires admin access.
    """
    repo = GPSDebugLogRepository(db)
    logs = await repo.get_recent_logs(limit)

    return [
        GPSDebugLogResponse(
            id=str(log.id),
            created_at=log.created_at,
            user_email=log.user_email,
            map_id=str(log.map_id),
            map_origin=log.map_origin,
            map_destination=log.map_destination,
            latitude=log.latitude,
            longitude=log.longitude,
            gps_accuracy=log.gps_accuracy,
            distance_from_origin_km=log.distance_from_origin_km,
            is_on_route=log.is_on_route,
            distance_to_route_m=log.distance_to_route_m,
            previous_pois=log.previous_pois,
            next_pois=log.next_pois,
            session_id=log.session_id,
        )
        for log in logs
    ]


@router.get("/map/{map_id}", response_model=List[GPSDebugLogResponse])
async def get_logs_by_map(
    map_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    """
    Get GPS debug logs for a specific map.

    Requires admin access.
    """
    repo = GPSDebugLogRepository(db)
    logs = await repo.get_logs_by_map(map_id, limit)

    return [
        GPSDebugLogResponse(
            id=str(log.id),
            created_at=log.created_at,
            user_email=log.user_email,
            map_id=str(log.map_id),
            map_origin=log.map_origin,
            map_destination=log.map_destination,
            latitude=log.latitude,
            longitude=log.longitude,
            gps_accuracy=log.gps_accuracy,
            distance_from_origin_km=log.distance_from_origin_km,
            is_on_route=log.is_on_route,
            distance_to_route_m=log.distance_to_route_m,
            previous_pois=log.previous_pois,
            next_pois=log.next_pois,
            session_id=log.session_id,
        )
        for log in logs
    ]


@router.delete("/cleanup")
async def cleanup_old_logs(
    days_to_keep: int = Query(30, ge=7, le=90, description="Days of logs to keep"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    """
    Remove old GPS debug logs.

    Deletes logs older than the specified number of days.
    Requires admin access.
    """
    repo = GPSDebugLogRepository(db)
    deleted_count = await repo.cleanup_old_logs(days_to_keep)

    await db.commit()

    return {
        "message": f"Deleted {deleted_count} log entries older than {days_to_keep} days",
        "deleted_count": deleted_count,
    }
