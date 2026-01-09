"""
Repository for application logs.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.application_log import ApplicationLog
from api.database.repositories.base import BaseRepository


# Log level name to numeric value mapping
LEVEL_MAP = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


class ApplicationLogRepository(BaseRepository[ApplicationLog]):
    """Repository for managing application logs."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ApplicationLog)

    async def create_log(
        self,
        level: str,
        level_no: int,
        module: str,
        message: str,
        timestamp: Optional[datetime] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_email: Optional[str] = None,
        func_name: Optional[str] = None,
        line_no: Optional[int] = None,
        exc_info: Optional[str] = None,
    ) -> ApplicationLog:
        """
        Create a new application log entry.

        Args:
            level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            level_no: Numeric log level
            module: Logger name (module path)
            message: Log message
            timestamp: When the log was created (default: now)
            request_id: Request ID for correlation
            session_id: Session ID for correlation
            user_email: User email for correlation
            func_name: Function name where log was created
            line_no: Line number where log was created
            exc_info: Exception traceback if any

        Returns:
            Created ApplicationLog instance
        """
        log = ApplicationLog(
            timestamp=timestamp or datetime.now(timezone.utc),
            level=level,
            level_no=level_no,
            module=module,
            message=message,
            request_id=request_id,
            session_id=session_id,
            user_email=user_email,
            func_name=func_name,
            line_no=line_no,
            exc_info=exc_info,
        )
        return await self.create(log)

    async def create_logs_batch(self, logs: List[Dict]) -> int:
        """
        Batch insert multiple log entries.

        Args:
            logs: List of dictionaries with log data

        Returns:
            Number of logs created
        """
        log_objects = [ApplicationLog(**log_data) for log_data in logs]
        self.session.add_all(log_objects)
        return len(log_objects)

    async def get_logs(
        self,
        level: Optional[str] = None,
        module: Optional[str] = None,
        user_email: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        search: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ApplicationLog], int]:
        """
        Get logs with filtering and pagination.

        When filtering by level, includes the selected level and all higher severity levels.
        For example, WARNING includes WARNING, ERROR, and CRITICAL.

        Args:
            level: Minimum log level (includes this level and higher)
            module: Logger name filter (exact match)
            user_email: User email filter
            session_id: Session ID filter
            request_id: Request ID filter
            search: Text search in message (partial match, case-insensitive)
            start_time: Start of time range
            end_time: End of time range
            skip: Number of records to skip (pagination offset)
            limit: Maximum records to return

        Returns:
            Tuple of (list of logs, total count)
        """
        # Build base query
        query = select(ApplicationLog)
        count_query = select(func.count(ApplicationLog.id))

        # Apply filters
        if level and level in LEVEL_MAP:
            level_no = LEVEL_MAP[level]
            query = query.where(ApplicationLog.level_no >= level_no)
            count_query = count_query.where(ApplicationLog.level_no >= level_no)

        if module:
            query = query.where(ApplicationLog.module == module)
            count_query = count_query.where(ApplicationLog.module == module)

        if user_email:
            query = query.where(ApplicationLog.user_email == user_email)
            count_query = count_query.where(ApplicationLog.user_email == user_email)

        if session_id:
            query = query.where(ApplicationLog.session_id == session_id)
            count_query = count_query.where(ApplicationLog.session_id == session_id)

        if request_id:
            query = query.where(ApplicationLog.request_id == request_id)
            count_query = count_query.where(ApplicationLog.request_id == request_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(ApplicationLog.message.ilike(search_pattern))
            count_query = count_query.where(ApplicationLog.message.ilike(search_pattern))

        if start_time:
            query = query.where(ApplicationLog.timestamp >= start_time)
            count_query = count_query.where(ApplicationLog.timestamp >= start_time)

        if end_time:
            query = query.where(ApplicationLog.timestamp <= end_time)
            count_query = count_query.where(ApplicationLog.timestamp <= end_time)

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(ApplicationLog.timestamp.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_modules(self) -> List[str]:
        """
        Get distinct module names for filter dropdown.

        Returns:
            List of unique module names sorted alphabetically
        """
        result = await self.session.execute(
            select(ApplicationLog.module)
            .distinct()
            .order_by(ApplicationLog.module)
        )
        return [row[0] for row in result.all()]

    async def get_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict:
        """
        Get log statistics by level.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary with counts per level and total
        """
        query = select(
            ApplicationLog.level,
            func.count(ApplicationLog.id).label("count"),
        )

        if start_time:
            query = query.where(ApplicationLog.timestamp >= start_time)
        if end_time:
            query = query.where(ApplicationLog.timestamp <= end_time)

        query = query.group_by(ApplicationLog.level)

        result = await self.session.execute(query)

        stats = {
            "debug": 0,
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
            "total": 0,
        }

        for row in result.all():
            level_key = row.level.lower()
            if level_key in stats:
                stats[level_key] = row.count
                stats["total"] += row.count

        return stats

    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        Remove logs older than specified days.

        Args:
            days_to_keep: Number of days of logs to keep (default: 30)

        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        result = await self.session.execute(
            delete(ApplicationLog).where(ApplicationLog.timestamp < cutoff_date)
        )
        return result.rowcount
