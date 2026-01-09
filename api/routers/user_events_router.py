"""
Router for user event analytics endpoints.

Provides endpoints for:
- Tracking user events from the frontend
- Admin endpoints for viewing analytics and statistics
"""

from datetime import datetime, timedelta


def utcnow() -> datetime:
    """Return current UTC time as naive datetime."""
    return datetime.utcnow()
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.user_event import UserEventRepository
from api.middleware.auth import get_current_admin
from api.models.base import UTCDatetime
from api.services.user_event_logger import user_event_logger

router = APIRouter(prefix="/api/events", tags=["User Events"])


# Request models
class TrackEventRequest(BaseModel):
    """Single event to track."""

    event_type: str = Field(..., description="Type of event")
    event_category: Optional[str] = Field(None, description="Category of event (auto-detected if not provided)")
    session_id: str = Field(..., description="Browser session ID")
    user_id: Optional[str] = Field(None, description="User UUID (optional for anonymous)")
    event_data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")
    device_type: Optional[str] = Field(None, description="Device type (mobile/tablet/desktop)")
    os: Optional[str] = Field(None, description="Operating system")
    browser: Optional[str] = Field(None, description="Browser name and version")
    screen_width: Optional[int] = Field(None, description="Screen width in pixels")
    screen_height: Optional[int] = Field(None, description="Screen height in pixels")
    page_path: Optional[str] = Field(None, description="Current page path")
    referrer: Optional[str] = Field(None, description="Referrer URL")
    latitude: Optional[float] = Field(None, description="User latitude")
    longitude: Optional[float] = Field(None, description="User longitude")
    duration_ms: Optional[int] = Field(None, description="Duration in ms (for performance events)")

    @field_validator("duration_ms", mode="before")
    @classmethod
    def convert_duration_to_int(cls, v: Any) -> Optional[int]:
        """Convert float duration to int (JavaScript may send floats)."""
        if v is None:
            return None
        return int(v)


class TrackEventsRequest(BaseModel):
    """Batch of events to track."""

    events: List[TrackEventRequest] = Field(..., description="List of events to track")


class TrackEventResponse(BaseModel):
    """Response after tracking events."""

    success: bool = Field(..., description="Whether events were queued successfully")
    queued_count: int = Field(..., description="Number of events queued")


# Response models for admin endpoints
class EventTypeStats(BaseModel):
    """Statistics for an event type."""

    event_category: str
    event_type: str
    count: int
    unique_sessions: int
    unique_users: int


class DeviceStats(BaseModel):
    """Device breakdown statistics."""

    device_type: Optional[str]
    os: Optional[str]
    browser: Optional[str]
    count: int
    unique_sessions: int


class DailyActiveUsers(BaseModel):
    """Daily active users statistics."""

    date: str
    unique_sessions: int
    unique_users: int
    total_events: int


class FeatureUsageStats(BaseModel):
    """Feature usage statistics."""

    feature: str
    count: int
    unique_sessions: int
    unique_users: int


class POIFilterUsageStats(BaseModel):
    """POI filter usage statistics."""

    filter_name: Optional[str]
    enabled: bool
    count: int


class ConversionFunnelStats(BaseModel):
    """Conversion funnel statistics."""

    search_started: Dict[str, int]
    search_completed: Dict[str, int]
    search_abandoned: Dict[str, int]
    map_create: Dict[str, int]
    map_adopt: Dict[str, int]
    completion_rate: float
    abandonment_rate: float
    map_creation_rate: float


class PerformanceStats(BaseModel):
    """Performance event statistics."""

    event_type: str
    count: int
    avg_duration_ms: float
    min_duration_ms: int
    max_duration_ms: int


class LoginLocation(BaseModel):
    """Login event with location data."""

    latitude: float
    longitude: float
    user_id: Optional[str]
    device_type: Optional[str]
    created_at: str
    user_email: Optional[str]
    user_name: Optional[str]


class UserEventResponse(BaseModel):
    """Single user event response."""

    id: str
    event_type: str
    event_category: str
    session_id: str
    user_id: Optional[str]
    device_type: Optional[str]
    os: Optional[str]
    browser: Optional[str]
    page_path: Optional[str]
    duration_ms: Optional[int]
    created_at: UTCDatetime


class StatsOverview(BaseModel):
    """Overview statistics response."""

    period_start: str
    period_end: str
    total_events: int
    unique_sessions: int
    unique_users: int


# Public endpoint for tracking events
@router.post("/track", response_model=TrackEventResponse)
async def track_events(
    request: TrackEventsRequest,
):
    """
    Track user events from the frontend.

    This endpoint accepts anonymous requests and queues events for batch processing.
    Events are stored for analytics and product improvement purposes.
    """
    events = [event.model_dump() for event in request.events]
    await user_event_logger.log_events_batch(events)

    return TrackEventResponse(
        success=True,
        queued_count=len(events),
    )


# Admin endpoints for viewing statistics
@router.get("/stats", response_model=StatsOverview)
async def get_stats_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get overview statistics.

    Returns total events, unique sessions, and unique users for the period.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    stats = await repo.get_overview_stats(start_date, end_date)
    return StatsOverview(**stats)


@router.get("/stats/events", response_model=List[EventTypeStats])
async def get_event_type_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics by event type.

    Returns event counts grouped by category and type.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    stats = await repo.get_stats_by_event_type(start_date, end_date)
    return [EventTypeStats(**s) for s in stats]


@router.get("/stats/features", response_model=List[FeatureUsageStats])
async def get_feature_usage_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get feature usage statistics.

    Returns usage counts for key features like map creation, search, export.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    stats = await repo.get_feature_usage(start_date, end_date)
    return [FeatureUsageStats(**s) for s in stats]


@router.get("/stats/devices", response_model=List[DeviceStats])
async def get_device_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get device breakdown statistics.

    Returns event counts grouped by device type, OS, and browser.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    stats = await repo.get_stats_by_device(start_date, end_date)
    return [DeviceStats(**s) for s in stats]


@router.get("/stats/poi-filters", response_model=List[POIFilterUsageStats])
async def get_poi_filter_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get POI filter usage statistics.

    Returns usage counts for each POI filter toggle.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    stats = await repo.get_poi_filter_usage(start_date, end_date)
    return [POIFilterUsageStats(**s) for s in stats]


@router.get("/stats/funnel", response_model=ConversionFunnelStats)
async def get_conversion_funnel(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get conversion funnel statistics.

    Returns funnel data: search started → search completed → map created/adopted.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    funnel = await repo.get_conversion_funnel(start_date, end_date)
    return ConversionFunnelStats(**funnel)


@router.get("/stats/daily", response_model=List[DailyActiveUsers])
async def get_daily_active_users(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily active users (DAU) statistics.

    Returns daily breakdown of unique sessions and users.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    stats = await repo.get_daily_active_users(days)
    return [DailyActiveUsers(**s) for s in stats]


@router.get("/stats/performance", response_model=List[PerformanceStats])
async def get_performance_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance event statistics.

    Returns performance metrics like map load time, search response time.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    stats = await repo.get_performance_stats(start_date, end_date)
    return [PerformanceStats(**s) for s in stats]


@router.get("/stats/login-locations", response_model=List[LoginLocation])
async def get_login_locations(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get login events with location data.

    Returns login events that have latitude/longitude for map visualization.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    locations = await repo.get_login_locations(start_date, end_date)
    return [LoginLocation(**loc) for loc in locations]


@router.get("/export/csv")
async def export_events_csv(
    days: int = Query(30, ge=1, le=365, description="Number of days to export"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Export events to CSV.

    Returns a CSV file with event data for the specified period.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    start_date = utcnow() - timedelta(days=days)
    end_date = utcnow()

    csv_content = await repo.export_to_csv(start_date, end_date)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=user_events_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
        },
    )


@router.delete("/cleanup")
async def cleanup_old_events(
    days_to_keep: int = Query(365, ge=30, le=730, description="Days of events to keep"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove old user events.

    Deletes events older than the specified number of days.
    Requires admin privileges.
    """
    repo = UserEventRepository(db)
    deleted_count = await repo.cleanup_old_events(days_to_keep)
    await db.commit()

    return {
        "message": f"Deleted {deleted_count} events older than {days_to_keep} days",
        "deleted_count": deleted_count,
    }
