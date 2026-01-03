"""
Custom logging handler that writes logs to the PostgreSQL database.

This handler accumulates logs in memory and periodically flushes them
to the database in batches for better performance.
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from api.middleware.request_id import get_request_id, get_session_id, get_user_email


class DatabaseLogHandler(logging.Handler):
    """
    A logging handler that writes log records to a PostgreSQL database.

    Features:
    - Batch writes: accumulates logs and writes in batches for performance
    - Async background task: flushes logs periodically without blocking
    - Graceful shutdown: ensures all logs are written on application exit
    - Error recovery: re-queues logs on database failure

    Usage:
        handler = DatabaseLogHandler.get_instance()
        logger.addHandler(handler)
    """

    _instance: Optional["DatabaseLogHandler"] = None
    _log_queue: List[Dict] = []
    _flush_task: Optional[asyncio.Task] = None
    _flush_interval: float = 5.0  # Flush every 5 seconds
    _batch_size: int = 100  # Or when we have 100 items
    _min_level: int = logging.INFO  # Minimum level to store in DB
    _initialized: bool = False
    _shutting_down: bool = False

    def __new__(cls, *args, **kwargs) -> "DatabaseLogHandler":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._log_queue = []
            cls._instance._flush_task = None
            cls._instance._initialized = False
            cls._instance._shutting_down = False
        return cls._instance

    def __init__(self, level: int = logging.INFO):
        """
        Initialize the handler.

        Args:
            level: Minimum log level to capture (default: INFO)
        """
        if self._initialized:
            return
        super().__init__(level)
        self._min_level = level
        self._initialized = True

    @classmethod
    def get_instance(cls, level: int = logging.INFO) -> "DatabaseLogHandler":
        """
        Get or create the singleton instance.

        Args:
            level: Minimum log level to capture

        Returns:
            The singleton DatabaseLogHandler instance
        """
        if cls._instance is None:
            cls._instance = cls(level)
        return cls._instance

    def emit(self, record: logging.LogRecord) -> None:
        """
        Process a log record.

        Args:
            record: The log record to process
        """
        if self._shutting_down:
            return

        # Skip logs below minimum level
        if record.levelno < self._min_level:
            return

        # Skip logs from this module to avoid recursion
        if record.name.startswith("api.services.database_log_handler"):
            return

        # Skip SQLAlchemy engine logs to avoid recursion
        if record.name.startswith("sqlalchemy.engine"):
            return

        try:
            # Format exception info if present
            exc_info_str = None
            if record.exc_info:
                exc_info_str = "".join(traceback.format_exception(*record.exc_info))

            # Get context variables
            request_id = get_request_id()
            session_id = get_session_id()
            user_email = get_user_email()

            # Create log entry dict
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created),
                "level": record.levelname,
                "level_no": record.levelno,
                "module": record.name,
                "message": record.getMessage(),
                "request_id": request_id,
                "session_id": session_id,
                "user_email": user_email,
                "func_name": record.funcName,
                "line_no": record.lineno,
                "exc_info": exc_info_str,
            }

            # Queue the log entry
            self._log_queue.append(log_entry)

            # Start flush task if not running
            try:
                loop = asyncio.get_running_loop()
                if self._flush_task is None or self._flush_task.done():
                    self._flush_task = loop.create_task(self._periodic_flush())

                # Flush immediately if batch is full
                if len(self._log_queue) >= self._batch_size:
                    loop.create_task(self._flush_logs())
            except RuntimeError:
                # No event loop running - logs will be flushed later
                pass

        except Exception:
            # Don't let logging errors propagate
            self.handleError(record)

    async def _periodic_flush(self) -> None:
        """Periodically flush queued logs."""
        while self._log_queue and not self._shutting_down:
            await asyncio.sleep(self._flush_interval)
            await self._flush_logs()

    async def _flush_logs(self) -> None:
        """Flush all queued logs to the database."""
        if not self._log_queue:
            return

        # Take current queue and clear it
        to_flush = self._log_queue[:]
        self._log_queue.clear()

        try:
            # Use standalone session to avoid event loop conflicts
            from sqlalchemy.ext.asyncio import (
                AsyncSession,
                async_sessionmaker,
                create_async_engine,
            )

            from api.providers.settings import get_settings

            settings = get_settings()
            database_url = (
                f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
                f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
            )
            engine = create_async_engine(
                database_url,
                pool_size=1,
                max_overflow=0,
                pool_pre_ping=True,
            )
            session_maker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            try:
                async with session_maker() as session:
                    try:
                        from api.database.repositories.application_log import (
                            ApplicationLogRepository,
                        )

                        repo = ApplicationLogRepository(session)
                        await repo.create_logs_batch(to_flush)
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
            finally:
                await engine.dispose()

        except Exception:
            # Re-queue logs for retry on failure
            # But limit queue size to avoid memory issues
            if len(self._log_queue) < 1000:
                self._log_queue.extend(to_flush)
            # Don't log the error here to avoid recursion

    async def flush_async(self) -> None:
        """Force flush all queued logs (async version)."""
        await self._flush_logs()

    async def shutdown(self) -> None:
        """
        Shutdown the handler, flushing remaining logs.

        Should be called during application shutdown.
        """
        self._shutting_down = True

        # Cancel periodic flush task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_logs()


# Global instance getter for convenience
def get_database_log_handler(level: int = logging.INFO) -> DatabaseLogHandler:
    """
    Get the singleton DatabaseLogHandler instance.

    Args:
        level: Minimum log level to capture

    Returns:
        The DatabaseLogHandler instance
    """
    return DatabaseLogHandler.get_instance(level)
