"""
Repository for API call logs.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.api_call_log import ApiCallLog
from api.database.repositories.base import BaseRepository


class ApiCallLogRepository(BaseRepository[ApiCallLog]):
    """Repository for managing API call logs."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ApiCallLog)

    async def create_log(
        self,
        provider: str,
        operation: str,
        endpoint: str,
        http_method: str,
        response_status: int,
        duration_ms: int,
        request_params: Optional[dict] = None,
        response_size_bytes: Optional[int] = None,
        cache_hit: bool = False,
        result_count: Optional[int] = None,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ApiCallLog:
        """
        Create a new API call log entry.

        Args:
            provider: API provider (osm, here, google_places)
            operation: Operation type (geocode, poi_search, etc.)
            endpoint: API endpoint URL
            http_method: HTTP method used
            response_status: HTTP response status code
            duration_ms: Request duration in milliseconds
            request_params: Request parameters (sanitized)
            response_size_bytes: Response size in bytes
            cache_hit: Whether this was a cache hit
            result_count: Number of results returned
            error_message: Error message if any
            session_id: Frontend session ID for correlation

        Returns:
            Created ApiCallLog instance
        """
        log = ApiCallLog(
            provider=provider,
            operation=operation,
            endpoint=endpoint,
            http_method=http_method,
            response_status=response_status,
            duration_ms=duration_ms,
            request_params=request_params,
            response_size_bytes=response_size_bytes,
            cache_hit=cache_hit,
            result_count=result_count,
            error_message=error_message,
            session_id=session_id,
        )
        return await self.create(log)

    async def get_stats_by_provider(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get aggregated statistics by provider.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with provider stats
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        result = await self.session.execute(
            select(
                ApiCallLog.provider,
                func.count(ApiCallLog.id).label("total_calls"),
                func.sum(
                    func.case((ApiCallLog.cache_hit == False, 1), else_=0)  # noqa: E712
                ).label("api_calls"),
                func.sum(
                    func.case((ApiCallLog.cache_hit == True, 1), else_=0)  # noqa: E712
                ).label("cache_hits"),
                func.avg(ApiCallLog.duration_ms).label("avg_duration_ms"),
                func.sum(ApiCallLog.response_size_bytes).label("total_bytes"),
            )
            .where(ApiCallLog.created_at >= start_date)
            .where(ApiCallLog.created_at <= end_date)
            .group_by(ApiCallLog.provider)
            .order_by(func.count(ApiCallLog.id).desc())
        )

        return [
            {
                "provider": row.provider,
                "total_calls": row.total_calls,
                "api_calls": row.api_calls or 0,
                "cache_hits": row.cache_hits or 0,
                "cache_hit_rate": (
                    (row.cache_hits / row.total_calls * 100)
                    if row.total_calls > 0 and row.cache_hits
                    else 0
                ),
                "avg_duration_ms": (
                    round(row.avg_duration_ms, 2) if row.avg_duration_ms else 0
                ),
                "total_bytes": row.total_bytes or 0,
            }
            for row in result.all()
        ]

    async def get_stats_by_operation(
        self,
        provider: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get aggregated statistics by operation type.

        Args:
            provider: Filter by provider (optional)
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with operation stats
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        query = (
            select(
                ApiCallLog.provider,
                ApiCallLog.operation,
                func.count(ApiCallLog.id).label("total_calls"),
                func.sum(
                    func.case((ApiCallLog.cache_hit == False, 1), else_=0)  # noqa: E712
                ).label("api_calls"),
                func.avg(ApiCallLog.duration_ms).label("avg_duration_ms"),
                func.sum(ApiCallLog.result_count).label("total_results"),
            )
            .where(ApiCallLog.created_at >= start_date)
            .where(ApiCallLog.created_at <= end_date)
        )

        if provider:
            query = query.where(ApiCallLog.provider == provider)

        query = query.group_by(ApiCallLog.provider, ApiCallLog.operation).order_by(
            ApiCallLog.provider, func.count(ApiCallLog.id).desc()
        )

        result = await self.session.execute(query)

        return [
            {
                "provider": row.provider,
                "operation": row.operation,
                "total_calls": row.total_calls,
                "api_calls": row.api_calls or 0,
                "avg_duration_ms": (
                    round(row.avg_duration_ms, 2) if row.avg_duration_ms else 0
                ),
                "total_results": row.total_results or 0,
            }
            for row in result.all()
        ]

    async def get_daily_stats(
        self,
        provider: Optional[str] = None,
        days: int = 30,
    ) -> List[Dict]:
        """
        Get daily call statistics.

        Args:
            provider: Filter by provider (optional)
            days: Number of days to look back

        Returns:
            List of dictionaries with daily stats
        """
        start_date = datetime.now() - timedelta(days=days)

        query = select(
            func.date(ApiCallLog.created_at).label("date"),
            ApiCallLog.provider,
            func.count(ApiCallLog.id).label("total_calls"),
            func.sum(
                func.case((ApiCallLog.cache_hit == False, 1), else_=0)  # noqa: E712
            ).label("api_calls"),
        ).where(ApiCallLog.created_at >= start_date)

        if provider:
            query = query.where(ApiCallLog.provider == provider)

        query = query.group_by(
            func.date(ApiCallLog.created_at), ApiCallLog.provider
        ).order_by(func.date(ApiCallLog.created_at).desc())

        result = await self.session.execute(query)

        return [
            {
                "date": str(row.date),
                "provider": row.provider,
                "total_calls": row.total_calls,
                "api_calls": row.api_calls or 0,
            }
            for row in result.all()
        ]

    async def get_recent_logs(
        self,
        provider: Optional[str] = None,
        operation: Optional[str] = None,
        limit: int = 100,
    ) -> List[ApiCallLog]:
        """
        Get recent API call logs.

        Args:
            provider: Filter by provider (optional)
            operation: Filter by operation (optional)
            limit: Maximum number of logs to return

        Returns:
            List of recent ApiCallLog instances
        """
        query = select(ApiCallLog)

        if provider:
            query = query.where(ApiCallLog.provider == provider)
        if operation:
            query = query.where(ApiCallLog.operation == operation)

        query = query.order_by(ApiCallLog.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_error_logs(
        self,
        start_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ApiCallLog]:
        """
        Get API call logs with errors.

        Args:
            start_date: Start of date range (default: 7 days ago)
            limit: Maximum number of logs to return

        Returns:
            List of ApiCallLog instances with errors
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)

        result = await self.session.execute(
            select(ApiCallLog)
            .where(ApiCallLog.created_at >= start_date)
            .where(ApiCallLog.response_status >= 400)
            .order_by(ApiCallLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_session_id(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[ApiCallLog]:
        """
        Get all API calls for a specific frontend session.

        Args:
            session_id: Frontend session UUID
            limit: Maximum number of records to return

        Returns:
            List of ApiCallLog instances
        """
        result = await self.session.execute(
            select(ApiCallLog)
            .where(ApiCallLog.session_id == session_id)
            .order_by(ApiCallLog.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Remove logs older than specified days.

        Args:
            days_to_keep: Number of days of logs to keep

        Returns:
            Number of deleted records
        """
        from sqlalchemy import delete

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        result = await self.session.execute(
            delete(ApiCallLog).where(ApiCallLog.created_at < cutoff_date)
        )
        return result.rowcount
