"""
Router for API call logs and statistics endpoints.

Provides endpoints for monitoring and analyzing external API calls
to OSM, HERE, and Google Places for cost tracking.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.repositories.api_call_log import ApiCallLogRepository

router = APIRouter(prefix="/api/api-logs", tags=["API Logs"])


class ProviderStats(BaseModel):
    """Statistics for a single provider."""

    provider: str
    total_calls: int
    api_calls: int  # Non-cache calls
    cache_hits: int
    cache_hit_rate: float
    avg_duration_ms: float
    total_bytes: int


class OperationStats(BaseModel):
    """Statistics for a single operation type."""

    provider: str
    operation: str
    total_calls: int
    api_calls: int
    avg_duration_ms: float
    total_results: int


class DailyStats(BaseModel):
    """Daily statistics."""

    date: str
    provider: str
    total_calls: int
    api_calls: int


class ApiCallLogResponse(BaseModel):
    """Single API call log entry."""

    id: str
    provider: str
    operation: str
    endpoint: str
    http_method: str
    response_status: int
    duration_ms: int
    response_size_bytes: Optional[int]
    cache_hit: bool
    result_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime


class StatsOverview(BaseModel):
    """Overview statistics response."""

    period_start: datetime
    period_end: datetime
    by_provider: List[ProviderStats]
    by_operation: List[OperationStats]


@router.get("/stats", response_model=StatsOverview)
async def get_api_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get API call statistics overview.

    Returns aggregated statistics by provider and operation for cost analysis.
    """
    repo = ApiCallLogRepository(db)

    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()

    provider_stats = await repo.get_stats_by_provider(start_date, end_date)
    operation_stats = await repo.get_stats_by_operation(provider, start_date, end_date)

    return StatsOverview(
        period_start=start_date,
        period_end=end_date,
        by_provider=[ProviderStats(**s) for s in provider_stats],
        by_operation=[OperationStats(**s) for s in operation_stats],
    )


@router.get("/stats/daily", response_model=List[DailyStats])
async def get_daily_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily API call statistics.

    Returns daily breakdown of API calls for trend analysis.
    """
    repo = ApiCallLogRepository(db)
    stats = await repo.get_daily_stats(provider, days)
    return [DailyStats(**s) for s in stats]


@router.get("/recent", response_model=List[ApiCallLogResponse])
async def get_recent_logs(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent API call logs.

    Returns the most recent API call logs for debugging and monitoring.
    """
    repo = ApiCallLogRepository(db)
    logs = await repo.get_recent_logs(provider, operation, limit)

    return [
        ApiCallLogResponse(
            id=str(log.id),
            provider=log.provider,
            operation=log.operation,
            endpoint=log.endpoint,
            http_method=log.http_method,
            response_status=log.response_status,
            duration_ms=log.duration_ms,
            response_size_bytes=log.response_size_bytes,
            cache_hit=log.cache_hit,
            result_count=log.result_count,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/errors", response_model=List[ApiCallLogResponse])
async def get_error_logs(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get API call logs with errors.

    Returns API calls that failed (HTTP status >= 400) for troubleshooting.
    """
    repo = ApiCallLogRepository(db)
    start_date = datetime.now() - timedelta(days=days)
    logs = await repo.get_error_logs(start_date, limit)

    return [
        ApiCallLogResponse(
            id=str(log.id),
            provider=log.provider,
            operation=log.operation,
            endpoint=log.endpoint,
            http_method=log.http_method,
            response_status=log.response_status,
            duration_ms=log.duration_ms,
            response_size_bytes=log.response_size_bytes,
            cache_hit=log.cache_hit,
            result_count=log.result_count,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.delete("/cleanup")
async def cleanup_old_logs(
    days_to_keep: int = Query(90, ge=7, le=365, description="Days of logs to keep"),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove old API call logs.

    Deletes logs older than the specified number of days to manage database size.
    """
    repo = ApiCallLogRepository(db)
    deleted_count = await repo.cleanup_old_logs(days_to_keep)

    return {
        "message": f"Deleted {deleted_count} log entries older than {days_to_keep} days",
        "deleted_count": deleted_count,
    }
