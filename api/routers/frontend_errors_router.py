"""
Router for frontend error logs endpoints.

Provides endpoints for receiving and analyzing frontend errors
reported by the client application.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.repositories.frontend_error_log import FrontendErrorLogRepository
from api.models.base import UTCDatetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/frontend-errors", tags=["Frontend Errors"])


# Request/Response Models


class FrontendErrorRequest(BaseModel):
    """Request body for reporting a frontend error."""

    session_id: str = Field(..., description="Frontend session UUID")
    error_type: str = Field(
        ..., description="Type of error (unhandled_error, react_error, api_error)"
    )
    message: str = Field(..., description="Error message")
    url: str = Field(..., description="URL where error occurred")
    stack_trace: Optional[str] = Field(None, description="JavaScript stack trace")
    component_stack: Optional[str] = Field(None, description="React component stack")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    extra_context: Optional[dict] = Field(None, description="Additional context data")


class FrontendErrorResponse(BaseModel):
    """Single frontend error log entry."""

    id: str
    session_id: str
    error_type: str
    message: str
    url: str
    user_agent: str
    stack_trace: Optional[str]
    component_stack: Optional[str]
    user_id: Optional[str]
    extra_context: Optional[dict]
    created_at: UTCDatetime


class ErrorStats(BaseModel):
    """Statistics for an error type."""

    error_type: str
    count: int
    unique_sessions: int
    unique_users: int


class TopError(BaseModel):
    """Most frequent error."""

    message: str
    error_type: str
    count: int
    last_seen: Optional[str]


class ErrorStatsOverview(BaseModel):
    """Overview of error statistics."""

    period_start: UTCDatetime
    period_end: UTCDatetime
    total_errors: int
    by_type: List[ErrorStats]
    top_errors: List[TopError]


# Endpoints


@router.post("", status_code=201)
async def report_error(
    error: FrontendErrorRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Report a frontend error.

    This endpoint is public and does not require authentication.
    It receives error reports from the frontend application.
    """
    repo = FrontendErrorLogRepository(db)

    # Extract user agent from request headers
    user_agent = request.headers.get("user-agent", "unknown")[:500]

    # Log the frontend error to application logs
    log_message = f"[FRONTEND {error.error_type.upper()}] {error.message}"
    if error.url:
        log_message += f" | URL: {error.url}"

    logger.error(
        log_message,
        extra={
            "frontend_error_type": error.error_type,
            "frontend_url": error.url,
            "frontend_session_id": error.session_id,
        }
    )

    await repo.create_log(
        session_id=error.session_id,
        error_type=error.error_type,
        message=error.message[:5000],  # Limit message length
        url=error.url[:2000],  # Limit URL length
        user_agent=user_agent,
        stack_trace=error.stack_trace[:10000] if error.stack_trace else None,
        component_stack=error.component_stack[:5000] if error.component_stack else None,
        user_id=error.user_id,
        extra_context=error.extra_context,
    )

    await db.commit()

    return {"status": "ok", "message": "Error logged successfully"}


@router.get("/stats", response_model=ErrorStatsOverview)
async def get_error_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get frontend error statistics overview.

    Returns aggregated statistics by error type for monitoring.
    Requires admin access.
    """
    repo = FrontendErrorLogRepository(db)

    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()

    type_stats = await repo.get_error_stats(start_date, end_date)
    top_errors = await repo.get_top_errors(start_date, limit=10)

    total_errors = sum(s["count"] for s in type_stats)

    return ErrorStatsOverview(
        period_start=start_date,
        period_end=end_date,
        total_errors=total_errors,
        by_type=[ErrorStats(**s) for s in type_stats],
        top_errors=[TopError(**e) for e in top_errors],
    )


@router.get("/recent", response_model=List[FrontendErrorResponse])
async def get_recent_errors(
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent frontend errors.

    Returns the most recent frontend errors for debugging.
    Requires admin access.
    """
    repo = FrontendErrorLogRepository(db)
    logs = await repo.get_recent_errors(error_type, user_id, limit)

    return [
        FrontendErrorResponse(
            id=str(log.id),
            session_id=log.session_id,
            error_type=log.error_type,
            message=log.message,
            url=log.url,
            user_agent=log.user_agent,
            stack_trace=log.stack_trace,
            component_stack=log.component_stack,
            user_id=log.user_id,
            extra_context=log.extra_context,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/session/{session_id}", response_model=List[FrontendErrorResponse])
async def get_session_errors(
    session_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all errors for a specific session.

    Returns all frontend errors for a given session ID.
    Requires admin access.
    """
    repo = FrontendErrorLogRepository(db)
    logs = await repo.get_by_session_id(session_id, limit)

    return [
        FrontendErrorResponse(
            id=str(log.id),
            session_id=log.session_id,
            error_type=log.error_type,
            message=log.message,
            url=log.url,
            user_agent=log.user_agent,
            stack_trace=log.stack_trace,
            component_stack=log.component_stack,
            user_id=log.user_id,
            extra_context=log.extra_context,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.delete("/cleanup")
async def cleanup_old_errors(
    days_to_keep: int = Query(30, ge=7, le=90, description="Days of logs to keep"),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove old frontend error logs.

    Deletes logs older than the specified number of days to manage database size.
    Requires admin access.
    """
    repo = FrontendErrorLogRepository(db)
    deleted_count = await repo.cleanup_old_logs(days_to_keep)

    await db.commit()

    return {
        "message": f"Deleted {deleted_count} error entries older than {days_to_keep} days",
        "deleted_count": deleted_count,
    }
