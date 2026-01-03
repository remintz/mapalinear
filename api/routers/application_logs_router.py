"""
Router for application logs viewing and filtering.

Provides admin endpoints for monitoring application logs stored in PostgreSQL.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.application_log import ApplicationLogRepository
from api.middleware.auth import get_current_admin

router = APIRouter(prefix="/api/admin/logs", tags=["Application Logs"])


class LogEntry(BaseModel):
    """Single application log entry."""

    id: str
    timestamp: datetime
    level: str
    module: str
    message: str
    request_id: Optional[str]
    session_id: Optional[str]
    user_email: Optional[str]
    func_name: Optional[str]
    line_no: Optional[int]
    exc_info: Optional[str]


class LogsResponse(BaseModel):
    """Paginated logs response."""

    logs: List[LogEntry]
    total: int
    skip: int
    limit: int


class LogStats(BaseModel):
    """Log statistics by level."""

    debug: int
    info: int
    warning: int
    error: int
    critical: int
    total: int


@router.get("", response_model=LogsResponse)
async def get_logs(
    level: Optional[str] = Query(
        None,
        description="Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). "
        "Includes selected level and all higher severity levels.",
    ),
    module: Optional[str] = Query(None, description="Logger module name filter"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    search: Optional[str] = Query(None, description="Text search in message (partial match)"),
    time_window: Optional[str] = Query(
        None,
        description="Predefined time window: 5m, 15m, 1h, 24h, or 'custom' for date range",
    ),
    start_time: Optional[datetime] = Query(
        None, description="Start of custom time range (ISO format)"
    ),
    end_time: Optional[datetime] = Query(
        None, description="End of custom time range (ISO format)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get application logs with filtering and pagination.

    Admin only endpoint. When filtering by level, includes the selected level
    and all higher severity levels (e.g., WARNING includes WARNING, ERROR, CRITICAL).
    """
    # Calculate time range based on time_window
    calculated_start = start_time
    calculated_end = end_time

    if time_window and time_window != "custom":
        now = datetime.now()
        calculated_end = now

        if time_window == "5m":
            calculated_start = now - timedelta(minutes=5)
        elif time_window == "15m":
            calculated_start = now - timedelta(minutes=15)
        elif time_window == "1h":
            calculated_start = now - timedelta(hours=1)
        elif time_window == "24h":
            calculated_start = now - timedelta(hours=24)

    repo = ApplicationLogRepository(db)
    logs, total = await repo.get_logs(
        level=level,
        module=module,
        user_email=user_email,
        session_id=session_id,
        request_id=request_id,
        search=search,
        start_time=calculated_start,
        end_time=calculated_end,
        skip=skip,
        limit=limit,
    )

    return LogsResponse(
        logs=[
            LogEntry(
                id=str(log.id),
                timestamp=log.timestamp,
                level=log.level,
                module=log.module,
                message=log.message,
                request_id=log.request_id,
                session_id=log.session_id,
                user_email=log.user_email,
                func_name=log.func_name,
                line_no=log.line_no,
                exc_info=log.exc_info,
            )
            for log in logs
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=LogStats)
async def get_log_stats(
    time_window: Optional[str] = Query(
        "24h",
        description="Time window: 5m, 15m, 1h, 24h, or 'custom' for date range",
    ),
    start_time: Optional[datetime] = Query(None, description="Start of custom range"),
    end_time: Optional[datetime] = Query(None, description="End of custom range"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get log statistics by level.

    Admin only endpoint. Returns counts for each log level within the time window.
    """
    # Calculate time range
    calculated_start = start_time
    calculated_end = end_time

    if time_window and time_window != "custom":
        now = datetime.now()
        calculated_end = now

        if time_window == "5m":
            calculated_start = now - timedelta(minutes=5)
        elif time_window == "15m":
            calculated_start = now - timedelta(minutes=15)
        elif time_window == "1h":
            calculated_start = now - timedelta(hours=1)
        elif time_window == "24h":
            calculated_start = now - timedelta(hours=24)

    repo = ApplicationLogRepository(db)
    stats = await repo.get_stats(start_time=calculated_start, end_time=calculated_end)

    return LogStats(**stats)


@router.get("/modules", response_model=List[str])
async def get_modules(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get list of all module names for filter dropdown.

    Admin only endpoint. Returns distinct module names from the logs.
    """
    repo = ApplicationLogRepository(db)
    return await repo.get_modules()


@router.delete("/cleanup")
async def cleanup_old_logs(
    days_to_keep: int = Query(30, ge=1, le=90, description="Days of logs to keep"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Remove old application logs.

    Admin only endpoint. Deletes logs older than the specified number of days.
    """
    repo = ApplicationLogRepository(db)
    deleted_count = await repo.cleanup_old_logs(days_to_keep)
    await db.commit()

    return {
        "message": f"Deleted {deleted_count} log entries older than {days_to_keep} days",
        "deleted_count": deleted_count,
    }
