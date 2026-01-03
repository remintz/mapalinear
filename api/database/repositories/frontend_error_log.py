"""
Repository for frontend error logs.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.frontend_error_log import FrontendErrorLog
from api.database.repositories.base import BaseRepository


class FrontendErrorLogRepository(BaseRepository[FrontendErrorLog]):
    """Repository for managing frontend error logs."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, FrontendErrorLog)

    async def create_log(
        self,
        session_id: str,
        error_type: str,
        message: str,
        url: str,
        user_agent: str,
        stack_trace: Optional[str] = None,
        component_stack: Optional[str] = None,
        user_id: Optional[str] = None,
        extra_context: Optional[dict] = None,
    ) -> FrontendErrorLog:
        """
        Create a new frontend error log entry.

        Args:
            session_id: Frontend session UUID
            error_type: Type of error (unhandled_error, react_error, etc.)
            message: Error message
            url: URL where error occurred
            user_agent: Browser/device info
            stack_trace: JavaScript stack trace
            component_stack: React component stack
            user_id: User ID if authenticated
            extra_context: Additional context data

        Returns:
            Created FrontendErrorLog instance
        """
        log = FrontendErrorLog(
            session_id=session_id,
            error_type=error_type,
            message=message,
            url=url,
            user_agent=user_agent,
            stack_trace=stack_trace,
            component_stack=component_stack,
            user_id=user_id,
            extra_context=extra_context,
        )
        return await self.create(log)

    async def get_by_session_id(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[FrontendErrorLog]:
        """
        Get all errors for a specific session.

        Args:
            session_id: Frontend session UUID
            limit: Maximum number of records to return

        Returns:
            List of FrontendErrorLog instances
        """
        result = await self.session.execute(
            select(FrontendErrorLog)
            .where(FrontendErrorLog.session_id == session_id)
            .order_by(FrontendErrorLog.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_errors(
        self,
        error_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[FrontendErrorLog]:
        """
        Get recent frontend errors.

        Args:
            error_type: Filter by error type (optional)
            user_id: Filter by user ID (optional)
            limit: Maximum number of records to return

        Returns:
            List of recent FrontendErrorLog instances
        """
        query = select(FrontendErrorLog)

        if error_type:
            query = query.where(FrontendErrorLog.error_type == error_type)
        if user_id:
            query = query.where(FrontendErrorLog.user_id == user_id)

        query = query.order_by(FrontendErrorLog.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_error_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get aggregated error statistics by type.

        Args:
            start_date: Start of date range (default: 7 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with error stats
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        result = await self.session.execute(
            select(
                FrontendErrorLog.error_type,
                func.count(FrontendErrorLog.id).label("count"),
                func.count(func.distinct(FrontendErrorLog.session_id)).label(
                    "unique_sessions"
                ),
                func.count(func.distinct(FrontendErrorLog.user_id)).label(
                    "unique_users"
                ),
            )
            .where(FrontendErrorLog.created_at >= start_date)
            .where(FrontendErrorLog.created_at <= end_date)
            .group_by(FrontendErrorLog.error_type)
            .order_by(func.count(FrontendErrorLog.id).desc())
        )

        return [
            {
                "error_type": row.error_type,
                "count": row.count,
                "unique_sessions": row.unique_sessions,
                "unique_users": row.unique_users or 0,
            }
            for row in result.all()
        ]

    async def get_top_errors(
        self,
        start_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get most frequent error messages.

        Args:
            start_date: Start of date range (default: 7 days ago)
            limit: Maximum number of unique errors to return

        Returns:
            List of dictionaries with error message stats
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)

        result = await self.session.execute(
            select(
                FrontendErrorLog.message,
                FrontendErrorLog.error_type,
                func.count(FrontendErrorLog.id).label("count"),
                func.max(FrontendErrorLog.created_at).label("last_seen"),
            )
            .where(FrontendErrorLog.created_at >= start_date)
            .group_by(FrontendErrorLog.message, FrontendErrorLog.error_type)
            .order_by(func.count(FrontendErrorLog.id).desc())
            .limit(limit)
        )

        return [
            {
                "message": row.message[:200] if row.message else "",
                "error_type": row.error_type,
                "count": row.count,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in result.all()
        ]

    async def get_errors_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[FrontendErrorLog]:
        """
        Get all errors for a specific user.

        Args:
            user_id: User UUID
            limit: Maximum number of records to return

        Returns:
            List of FrontendErrorLog instances
        """
        result = await self.session.execute(
            select(FrontendErrorLog)
            .where(FrontendErrorLog.user_id == user_id)
            .order_by(FrontendErrorLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        Remove logs older than specified days.

        Args:
            days_to_keep: Number of days of logs to keep

        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        result = await self.session.execute(
            delete(FrontendErrorLog).where(FrontendErrorLog.created_at < cutoff_date)
        )
        return result.rowcount
