"""
Service for logging user events to the database.

This service provides a simple interface for tracking user behavior,
feature usage, errors, and performance metrics for analytics.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from api.database.models.event_types import get_category_for_event_type
from api.database.repositories.user_event import UserEventRepository

logger = logging.getLogger(__name__)


@dataclass
class UserEventContext:
    """Context for a user event."""

    event_type: str
    event_category: str
    session_id: str
    user_id: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    page_path: Optional[str] = None
    referrer: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class UserEventLogger:
    """
    Service for logging user events.

    Usage:
        # Simple event logging
        await user_event_logger.log_event(
            event_type="page_view",
            session_id="abc123",
            page_path="/map",
        )

        # With device info
        await user_event_logger.log_event(
            event_type="poi_click",
            session_id="abc123",
            user_id="user-uuid",
            event_data={"poi_id": "poi-123", "poi_name": "Gas Station"},
            device_type="mobile",
            os="iOS 17",
            browser="Safari 17",
        )
    """

    _instance: Optional["UserEventLogger"] = None
    _event_queue: List[UserEventContext] = []
    _flush_task: Optional[asyncio.Task] = None
    _flush_interval: float = 5.0  # Flush every 5 seconds
    _batch_size: int = 100  # Or when we have 100 items

    def __new__(cls) -> "UserEventLogger":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._event_queue = []
            cls._instance._flush_task = None
        return cls._instance

    async def log_event(
        self,
        event_type: str,
        session_id: str,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        device_type: Optional[str] = None,
        os: Optional[str] = None,
        browser: Optional[str] = None,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        page_path: Optional[str] = None,
        referrer: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log a user event.

        Args:
            event_type: Type of event (e.g., "login", "page_view")
            session_id: Browser session ID (required)
            event_category: Category of event (auto-detected if not provided)
            user_id: User UUID (optional for anonymous)
            event_data: Additional event-specific data
            device_type: Device type (mobile/tablet/desktop)
            os: Operating system
            browser: Browser name and version
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            page_path: Current page path
            referrer: Referrer URL
            latitude: User latitude (if available)
            longitude: User longitude (if available)
            duration_ms: Duration in ms (for performance events)
            error_message: Error message (for error events)
        """
        # Auto-detect category if not provided
        if event_category is None:
            event_category = get_category_for_event_type(event_type)
            if event_category is None:
                event_category = "interaction"  # Default category

        ctx = UserEventContext(
            event_type=event_type,
            event_category=event_category,
            session_id=session_id,
            user_id=user_id,
            event_data=event_data,
            device_type=device_type,
            os=os,
            browser=browser,
            screen_width=screen_width,
            screen_height=screen_height,
            page_path=page_path,
            referrer=referrer,
            latitude=latitude,
            longitude=longitude,
            duration_ms=duration_ms,
            error_message=error_message[:1000] if error_message else None,
        )

        await self._queue_event(ctx)

    async def log_events_batch(
        self,
        events: List[Dict[str, Any]],
    ) -> None:
        """
        Log multiple events in batch.

        Args:
            events: List of event dictionaries
        """
        for event in events:
            # Auto-detect category if not provided
            event_category = event.get("event_category")
            if event_category is None:
                event_category = get_category_for_event_type(event.get("event_type", ""))
                if event_category is None:
                    event_category = "interaction"

            ctx = UserEventContext(
                event_type=event.get("event_type", "unknown"),
                event_category=event_category,
                session_id=event.get("session_id", ""),
                user_id=event.get("user_id"),
                event_data=event.get("event_data"),
                device_type=event.get("device_type"),
                os=event.get("os"),
                browser=event.get("browser"),
                screen_width=event.get("screen_width"),
                screen_height=event.get("screen_height"),
                page_path=event.get("page_path"),
                referrer=event.get("referrer"),
                latitude=event.get("latitude"),
                longitude=event.get("longitude"),
                duration_ms=event.get("duration_ms"),
                error_message=event.get("error_message", "")[:1000] if event.get("error_message") else None,
            )
            self._event_queue.append(ctx)

        # Start flush task if not running
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

        # Flush immediately if batch is full
        if len(self._event_queue) >= self._batch_size:
            await self._flush_events()

    async def _queue_event(self, ctx: UserEventContext) -> None:
        """Queue an event for batch insertion."""
        self._event_queue.append(ctx)

        # Start flush task if not running
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

        # Flush immediately if batch is full
        if len(self._event_queue) >= self._batch_size:
            await self._flush_events()

    async def _periodic_flush(self) -> None:
        """Periodically flush queued events."""
        while self._event_queue:
            await asyncio.sleep(self._flush_interval)
            await self._flush_events()

    async def _flush_events(self) -> None:
        """Flush all queued events to the database."""
        if not self._event_queue:
            return

        # Take current queue and clear it
        to_flush = self._event_queue[:]
        self._event_queue.clear()

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
                        repo = UserEventRepository(session)

                        for ctx in to_flush:
                            await repo.create_event(
                                event_type=ctx.event_type,
                                event_category=ctx.event_category,
                                session_id=ctx.session_id,
                                user_id=ctx.user_id,
                                event_data=ctx.event_data,
                                device_type=ctx.device_type,
                                os=ctx.os,
                                browser=ctx.browser,
                                screen_width=ctx.screen_width,
                                screen_height=ctx.screen_height,
                                page_path=ctx.page_path,
                                referrer=ctx.referrer,
                                latitude=ctx.latitude,
                                longitude=ctx.longitude,
                                duration_ms=ctx.duration_ms,
                                error_message=ctx.error_message,
                            )
                        await session.commit()
                        logger.debug(f"Flushed {len(to_flush)} user events to database")
                    except Exception:
                        await session.rollback()
                        raise
            finally:
                await engine.dispose()

        except Exception as e:
            logger.error(f"Failed to flush user events: {e}")
            # Put items back in queue for retry
            self._event_queue.extend(to_flush)

    async def flush(self) -> None:
        """Force flush all queued events."""
        await self._flush_events()

    async def shutdown(self) -> None:
        """Shutdown the logger, flushing remaining events."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        await self._flush_events()

    # Helper methods for common event types
    async def log_page_view(
        self,
        session_id: str,
        page_path: str,
        user_id: Optional[str] = None,
        referrer: Optional[str] = None,
        device_type: Optional[str] = None,
        os: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> None:
        """Log a page view event."""
        await self.log_event(
            event_type="page_view",
            event_category="navigation",
            session_id=session_id,
            user_id=user_id,
            page_path=page_path,
            referrer=referrer,
            device_type=device_type,
            os=os,
            browser=browser,
        )

    async def log_login(
        self,
        session_id: str,
        user_id: str,
        device_type: Optional[str] = None,
        os: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> None:
        """Log a login event."""
        await self.log_event(
            event_type="login",
            event_category="auth",
            session_id=session_id,
            user_id=user_id,
            device_type=device_type,
            os=os,
            browser=browser,
        )

    async def log_logout(
        self,
        session_id: str,
        user_id: str,
    ) -> None:
        """Log a logout event."""
        await self.log_event(
            event_type="logout",
            event_category="auth",
            session_id=session_id,
            user_id=user_id,
        )

    async def log_error(
        self,
        session_id: str,
        event_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        page_path: Optional[str] = None,
    ) -> None:
        """Log an error event."""
        await self.log_event(
            event_type=event_type,
            event_category="error",
            session_id=session_id,
            user_id=user_id,
            error_message=error_message,
            event_data=event_data,
            page_path=page_path,
        )

    async def log_performance(
        self,
        session_id: str,
        event_type: str,
        duration_ms: int,
        user_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        page_path: Optional[str] = None,
    ) -> None:
        """Log a performance event."""
        await self.log_event(
            event_type=event_type,
            event_category="performance",
            session_id=session_id,
            user_id=user_id,
            duration_ms=duration_ms,
            event_data=event_data,
            page_path=page_path,
        )

    async def log_map_event(
        self,
        session_id: str,
        event_type: str,
        user_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a map management event."""
        await self.log_event(
            event_type=event_type,
            event_category="map_management",
            session_id=session_id,
            user_id=user_id,
            event_data=event_data,
        )

    async def log_conversion(
        self,
        session_id: str,
        event_type: str,
        user_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a conversion funnel event."""
        await self.log_event(
            event_type=event_type,
            event_category="conversion",
            session_id=session_id,
            user_id=user_id,
            event_data=event_data,
        )


# Global instance
user_event_logger = UserEventLogger()
