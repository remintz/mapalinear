"""
Router for session activity endpoints.

Provides endpoints for viewing unified session activity including
frontend errors and API calls correlated by session ID.
"""

from datetime import datetime
from typing import List, Literal, Optional, Union

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.repositories.api_call_log import ApiCallLogRepository
from api.database.repositories.frontend_error_log import FrontendErrorLogRepository

router = APIRouter(prefix="/api/sessions", tags=["Session Activity"])


# Response Models


class ApiCallEvent(BaseModel):
    """API call event in the timeline."""

    event_type: Literal["api_call"] = "api_call"
    timestamp: datetime
    id: str
    provider: str
    operation: str
    endpoint: str
    http_method: str
    response_status: int
    duration_ms: int
    cache_hit: bool
    error_message: Optional[str]


class FrontendErrorEvent(BaseModel):
    """Frontend error event in the timeline."""

    event_type: Literal["frontend_error"] = "frontend_error"
    timestamp: datetime
    id: str
    error_type: str
    message: str
    url: str
    stack_trace: Optional[str]
    component_stack: Optional[str]


TimelineEvent = Union[ApiCallEvent, FrontendErrorEvent]


class SessionSummary(BaseModel):
    """Summary of session activity."""

    session_id: str
    first_activity: Optional[datetime]
    last_activity: Optional[datetime]
    total_api_calls: int
    total_errors: int
    error_rate: float  # Percentage of events that are errors


class SessionActivityResponse(BaseModel):
    """Complete session activity response."""

    session_id: str
    summary: SessionSummary
    timeline: List[TimelineEvent]


# Endpoints


@router.get("/{session_id}/activity", response_model=SessionActivityResponse)
async def get_session_activity(
    session_id: str,
    limit: int = Query(200, ge=1, le=1000, description="Maximum events to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete activity for a session.

    Returns a unified timeline of API calls and frontend errors
    for a specific session, sorted by timestamp.
    Useful for debugging user-reported issues.

    Requires admin access.
    """
    api_repo = ApiCallLogRepository(db)
    error_repo = FrontendErrorLogRepository(db)

    # Fetch both types of events
    api_calls = await api_repo.get_by_session_id(session_id, limit)
    frontend_errors = await error_repo.get_by_session_id(session_id, limit)

    # Build timeline events
    timeline: List[TimelineEvent] = []

    for call in api_calls:
        timeline.append(
            ApiCallEvent(
                timestamp=call.created_at,
                id=str(call.id),
                provider=call.provider,
                operation=call.operation,
                endpoint=call.endpoint,
                http_method=call.http_method,
                response_status=call.response_status,
                duration_ms=call.duration_ms,
                cache_hit=call.cache_hit,
                error_message=call.error_message,
            )
        )

    for error in frontend_errors:
        timeline.append(
            FrontendErrorEvent(
                timestamp=error.created_at,
                id=str(error.id),
                error_type=error.error_type,
                message=error.message[:500],  # Truncate for overview
                url=error.url,
                stack_trace=error.stack_trace[:1000] if error.stack_trace else None,
                component_stack=(
                    error.component_stack[:500] if error.component_stack else None
                ),
            )
        )

    # Sort by timestamp
    timeline.sort(key=lambda x: x.timestamp)

    # Limit to requested number
    timeline = timeline[:limit]

    # Calculate summary
    total_api_calls = len(api_calls)
    total_errors = len(frontend_errors)
    total_events = total_api_calls + total_errors

    first_activity = timeline[0].timestamp if timeline else None
    last_activity = timeline[-1].timestamp if timeline else None

    error_rate = (total_errors / total_events * 100) if total_events > 0 else 0

    summary = SessionSummary(
        session_id=session_id,
        first_activity=first_activity,
        last_activity=last_activity,
        total_api_calls=total_api_calls,
        total_errors=total_errors,
        error_rate=round(error_rate, 2),
    )

    return SessionActivityResponse(
        session_id=session_id,
        summary=summary,
        timeline=timeline,
    )


@router.get("/{session_id}/errors", response_model=List[FrontendErrorEvent])
async def get_session_errors_only(
    session_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum errors to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get only frontend errors for a session.

    Returns frontend errors for a specific session, sorted by timestamp.
    Useful for quickly checking errors without full activity context.

    Requires admin access.
    """
    error_repo = FrontendErrorLogRepository(db)
    frontend_errors = await error_repo.get_by_session_id(session_id, limit)

    return [
        FrontendErrorEvent(
            timestamp=error.created_at,
            id=str(error.id),
            error_type=error.error_type,
            message=error.message,
            url=error.url,
            stack_trace=error.stack_trace,
            component_stack=error.component_stack,
        )
        for error in frontend_errors
    ]


@router.get("/{session_id}/api-calls", response_model=List[ApiCallEvent])
async def get_session_api_calls_only(
    session_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum calls to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get only API calls for a session.

    Returns API calls for a specific session, sorted by timestamp.
    Useful for analyzing API usage patterns.

    Requires admin access.
    """
    api_repo = ApiCallLogRepository(db)
    api_calls = await api_repo.get_by_session_id(session_id, limit)

    return [
        ApiCallEvent(
            timestamp=call.created_at,
            id=str(call.id),
            provider=call.provider,
            operation=call.operation,
            endpoint=call.endpoint,
            http_method=call.http_method,
            response_status=call.response_status,
            duration_ms=call.duration_ms,
            cache_hit=call.cache_hit,
            error_message=call.error_message,
        )
        for call in api_calls
    ]
