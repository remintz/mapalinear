"""
Service for logging external API calls to the database.

This service provides a simple interface for tracking all external API calls
(OSM, HERE, Google Places) for cost monitoring and analysis.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from api.database.repositories.api_call_log import ApiCallLogRepository

logger = logging.getLogger(__name__)


# Sensitive keys to remove from request params
SENSITIVE_KEYS = {
    "apiKey",
    "api_key",
    "apikey",
    "key",
    "X-Goog-Api-Key",
    "token",
    "password",
}


def sanitize_params(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Remove sensitive information from request parameters.

    Args:
        params: Original request parameters

    Returns:
        Sanitized parameters with sensitive values removed
    """
    if params is None:
        return None

    sanitized = {}
    for key, value in params.items():
        if key in SENSITIVE_KEYS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_params(value)
        else:
            sanitized[key] = value
    return sanitized


@dataclass
class ApiCallContext:
    """Context for tracking an API call."""

    provider: str
    operation: str
    endpoint: str
    http_method: str = "GET"
    request_params: Optional[Dict[str, Any]] = None
    start_time: float = 0.0
    session_id: Optional[str] = None  # Frontend session correlation

    # Results to be filled after the call
    response_status: int = 0
    response_size_bytes: Optional[int] = None
    cache_hit: bool = False
    result_count: Optional[int] = None
    error_message: Optional[str] = None


class ApiCallLogger:
    """
    Service for logging API calls to external providers.

    Usage:
        async with api_call_logger.track_call(
            provider="osm",
            operation="poi_search",
            endpoint="https://overpass-api.de/api/interpreter",
            http_method="POST",
            request_params={"query": "..."}
        ) as ctx:
            # Make the API call
            response = await client.post(...)
            ctx.response_status = response.status_code
            ctx.response_size_bytes = len(response.content)
            ctx.result_count = len(results)
    """

    _instance: Optional["ApiCallLogger"] = None
    _log_queue: List[ApiCallContext] = []
    _flush_task: Optional[asyncio.Task] = None
    _flush_interval: float = 5.0  # Flush every 5 seconds
    _batch_size: int = 50  # Or when we have 50 items

    def __new__(cls) -> "ApiCallLogger":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._log_queue = []
            cls._instance._flush_task = None
        return cls._instance

    @asynccontextmanager
    async def track_call(
        self,
        provider: str,
        operation: str,
        endpoint: str,
        http_method: str = "GET",
        request_params: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ):
        """
        Context manager for tracking an API call.

        Args:
            provider: API provider (osm, here, google_places)
            operation: Operation type (geocode, poi_search, etc.)
            endpoint: API endpoint URL
            http_method: HTTP method (GET, POST, etc.)
            request_params: Request parameters (will be sanitized)
            session_id: Frontend session ID for correlation

        Yields:
            ApiCallContext to fill with response details
        """
        ctx = ApiCallContext(
            provider=provider,
            operation=operation,
            endpoint=endpoint,
            http_method=http_method,
            request_params=sanitize_params(request_params),
            start_time=time.time(),
            session_id=session_id,
        )

        try:
            yield ctx
        except Exception as e:
            ctx.error_message = str(e)[:1000]  # Truncate error message
            ctx.response_status = 500
            raise
        finally:
            # Calculate duration
            duration_ms = int((time.time() - ctx.start_time) * 1000)

            # Queue the log entry
            await self._queue_log(ctx, duration_ms)

    async def _queue_log(self, ctx: ApiCallContext, duration_ms: int) -> None:
        """Queue a log entry for batch insertion."""
        self._log_queue.append((ctx, duration_ms))

        # Start flush task if not running
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

        # Flush immediately if batch is full
        if len(self._log_queue) >= self._batch_size:
            await self._flush_logs()

    async def _periodic_flush(self) -> None:
        """Periodically flush queued logs."""
        while self._log_queue:
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
            # when called from background threads
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
                        repo = ApiCallLogRepository(session)

                        for ctx, duration_ms in to_flush:
                            await repo.create_log(
                                provider=ctx.provider,
                                operation=ctx.operation,
                                endpoint=ctx.endpoint,
                                http_method=ctx.http_method,
                                response_status=ctx.response_status,
                                duration_ms=duration_ms,
                                request_params=ctx.request_params,
                                response_size_bytes=ctx.response_size_bytes,
                                cache_hit=ctx.cache_hit,
                                result_count=ctx.result_count,
                                error_message=ctx.error_message,
                                session_id=ctx.session_id,
                            )
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
            finally:
                await engine.dispose()

        except Exception as e:
            logger.error(f"Failed to flush API call logs: {e}")
            # Put items back in queue for retry
            self._log_queue.extend(to_flush)

    async def log_call(
        self,
        provider: str,
        operation: str,
        endpoint: str,
        http_method: str,
        response_status: int,
        duration_ms: int,
        request_params: Optional[Dict[str, Any]] = None,
        response_size_bytes: Optional[int] = None,
        cache_hit: bool = False,
        result_count: Optional[int] = None,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log an API call directly (alternative to context manager).

        Args:
            provider: API provider
            operation: Operation type
            endpoint: API endpoint
            http_method: HTTP method
            response_status: HTTP response status
            duration_ms: Request duration in ms
            request_params: Request parameters
            response_size_bytes: Response size
            cache_hit: Whether it was a cache hit
            result_count: Number of results
            error_message: Error message if any
            session_id: Frontend session ID for correlation
        """
        ctx = ApiCallContext(
            provider=provider,
            operation=operation,
            endpoint=endpoint,
            http_method=http_method,
            request_params=sanitize_params(request_params),
            response_status=response_status,
            response_size_bytes=response_size_bytes,
            cache_hit=cache_hit,
            result_count=result_count,
            error_message=error_message,
            session_id=session_id,
        )
        await self._queue_log(ctx, duration_ms)

    async def log_cache_hit(
        self,
        provider: str,
        operation: str,
        request_params: Optional[Dict[str, Any]] = None,
        result_count: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log a cache hit (no actual API call made).

        Args:
            provider: API provider
            operation: Operation type
            request_params: Request parameters
            result_count: Number of cached results
            session_id: Frontend session ID for correlation
        """
        await self.log_call(
            provider=provider,
            operation=operation,
            endpoint="cache",
            http_method="CACHE",
            response_status=200,
            duration_ms=0,
            request_params=request_params,
            cache_hit=True,
            result_count=result_count,
            session_id=session_id,
        )

    async def flush(self) -> None:
        """Force flush all queued logs."""
        await self._flush_logs()

    async def shutdown(self) -> None:
        """Shutdown the logger, flushing remaining logs."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        await self._flush_logs()


# Global instance
api_call_logger = ApiCallLogger()


# Helper functions for common operations
async def log_osm_call(
    operation: str,
    endpoint: str,
    http_method: str,
    response_status: int,
    duration_ms: int,
    request_params: Optional[Dict[str, Any]] = None,
    response_size_bytes: Optional[int] = None,
    result_count: Optional[int] = None,
    error_message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Log an OSM API call."""
    await api_call_logger.log_call(
        provider="osm",
        operation=operation,
        endpoint=endpoint,
        http_method=http_method,
        response_status=response_status,
        duration_ms=duration_ms,
        request_params=request_params,
        response_size_bytes=response_size_bytes,
        cache_hit=False,
        result_count=result_count,
        error_message=error_message,
        session_id=session_id,
    )


async def log_here_call(
    operation: str,
    endpoint: str,
    http_method: str,
    response_status: int,
    duration_ms: int,
    request_params: Optional[Dict[str, Any]] = None,
    response_size_bytes: Optional[int] = None,
    result_count: Optional[int] = None,
    error_message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Log a HERE API call."""
    await api_call_logger.log_call(
        provider="here",
        operation=operation,
        endpoint=endpoint,
        http_method=http_method,
        response_status=response_status,
        duration_ms=duration_ms,
        request_params=request_params,
        response_size_bytes=response_size_bytes,
        cache_hit=False,
        result_count=result_count,
        error_message=error_message,
        session_id=session_id,
    )


async def log_google_places_call(
    operation: str,
    endpoint: str,
    http_method: str,
    response_status: int,
    duration_ms: int,
    request_params: Optional[Dict[str, Any]] = None,
    response_size_bytes: Optional[int] = None,
    result_count: Optional[int] = None,
    error_message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Log a Google Places API call."""
    await api_call_logger.log_call(
        provider="google_places",
        operation=operation,
        endpoint=endpoint,
        http_method=http_method,
        response_status=response_status,
        duration_ms=duration_ms,
        request_params=request_params,
        response_size_bytes=response_size_bytes,
        cache_hit=False,
        result_count=result_count,
        error_message=error_message,
        session_id=session_id,
    )
