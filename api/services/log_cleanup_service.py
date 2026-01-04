"""
Periodic log cleanup service.

This service runs in the background and periodically deletes old logs
from the database based on the configured retention period.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_session
from api.database.models.application_log import ApplicationLog
from api.database.models.api_call_log import ApiCallLog
from api.database.models.frontend_error_log import FrontendErrorLog
from api.database.repositories.system_settings import SystemSettingsRepository

logger = logging.getLogger(__name__)


class LogCleanupService:
    """
    Service for periodically cleaning up old logs from the database.

    Runs every 24 hours and deletes logs older than the configured
    retention period (default: 7 days).
    """

    _instance: Optional["LogCleanupService"] = None
    _task: Optional[asyncio.Task] = None
    _running: bool = False

    # Run cleanup every 24 hours (in seconds)
    CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60

    # Default retention days if setting is not found
    DEFAULT_RETENTION_DAYS = 7

    @classmethod
    def get_instance(cls) -> "LogCleanupService":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the periodic cleanup task."""
        if self._running:
            logger.warning("Log cleanup service is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Log cleanup service started")

    async def stop(self) -> None:
        """Stop the periodic cleanup task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Log cleanup service stopped")

    async def _cleanup_loop(self) -> None:
        """Main loop that runs cleanup periodically."""
        # Run initial cleanup after a short delay (let the app fully start)
        await asyncio.sleep(60)  # Wait 1 minute after startup

        while self._running:
            try:
                await self._run_cleanup()
            except Exception as e:
                logger.error(f"Error during log cleanup: {e}", exc_info=True)

            # Wait for next cleanup cycle
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break

    async def _get_retention_days(self, session: AsyncSession) -> int:
        """Get the configured log retention period in days."""
        repo = SystemSettingsRepository(session)
        value = await repo.get_value("log_retention_days")

        if value:
            try:
                days = int(value)
                if 1 <= days <= 365:
                    return days
            except ValueError:
                pass

        return self.DEFAULT_RETENTION_DAYS

    async def _run_cleanup(self) -> None:
        """Execute the cleanup of old logs."""
        async with get_session() as session:
            retention_days = await self._get_retention_days(session)
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            logger.info(
                f"Starting log cleanup: removing logs older than {retention_days} days "
                f"(before {cutoff_date.isoformat()})"
            )

            total_deleted = 0

            # Clean up application logs
            app_logs_deleted = await self._delete_old_logs(
                session, ApplicationLog, "timestamp", cutoff_date
            )
            total_deleted += app_logs_deleted

            # Clean up API call logs
            api_logs_deleted = await self._delete_old_logs(
                session, ApiCallLog, "created_at", cutoff_date
            )
            total_deleted += api_logs_deleted

            # Clean up frontend error logs
            frontend_logs_deleted = await self._delete_old_logs(
                session, FrontendErrorLog, "created_at", cutoff_date
            )
            total_deleted += frontend_logs_deleted

            await session.commit()

            if total_deleted > 0:
                logger.info(
                    f"Log cleanup completed: deleted {total_deleted} logs "
                    f"(app: {app_logs_deleted}, api: {api_logs_deleted}, "
                    f"frontend: {frontend_logs_deleted})"
                )
            else:
                logger.debug("Log cleanup completed: no old logs to delete")

    async def _delete_old_logs(
        self,
        session: AsyncSession,
        model,
        timestamp_column: str,
        cutoff_date: datetime,
    ) -> int:
        """Delete logs older than the cutoff date for a specific model."""
        try:
            column = getattr(model, timestamp_column)

            # First count how many will be deleted
            count_result = await session.execute(
                select(func.count()).select_from(model).where(column < cutoff_date)
            )
            count = count_result.scalar() or 0

            if count > 0:
                # Delete in batches to avoid locking issues
                batch_size = 1000
                deleted = 0

                while deleted < count:
                    # Get IDs to delete in this batch
                    ids_result = await session.execute(
                        select(model.id).where(column < cutoff_date).limit(batch_size)
                    )
                    ids_to_delete = [row[0] for row in ids_result.fetchall()]

                    if not ids_to_delete:
                        break

                    await session.execute(
                        delete(model).where(model.id.in_(ids_to_delete))
                    )
                    deleted += len(ids_to_delete)

                    # Flush after each batch
                    await session.flush()

                logger.debug(f"Deleted {deleted} old {model.__tablename__} entries")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Error deleting old {model.__tablename__}: {e}")
            return 0

    async def run_manual_cleanup(self) -> dict:
        """
        Run cleanup manually (e.g., triggered by admin).

        Returns:
            Dictionary with cleanup statistics
        """
        async with get_session() as session:
            retention_days = await self._get_retention_days(session)
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            app_logs_deleted = await self._delete_old_logs(
                session, ApplicationLog, "timestamp", cutoff_date
            )
            api_logs_deleted = await self._delete_old_logs(
                session, ApiCallLog, "created_at", cutoff_date
            )
            frontend_logs_deleted = await self._delete_old_logs(
                session, FrontendErrorLog, "created_at", cutoff_date
            )

            await session.commit()

            return {
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "application_logs_deleted": app_logs_deleted,
                "api_logs_deleted": api_logs_deleted,
                "frontend_logs_deleted": frontend_logs_deleted,
                "total_deleted": app_logs_deleted + api_logs_deleted + frontend_logs_deleted,
            }


def get_log_cleanup_service() -> LogCleanupService:
    """Get the log cleanup service instance."""
    return LogCleanupService.get_instance()
