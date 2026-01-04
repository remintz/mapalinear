"""
Unit tests for api/services/user_event_logger.py

Tests for user event logging functionality:
- Event logging
- Batch logging
- Category auto-detection
- Helper methods
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.user_event_logger import (
    UserEventLogger,
    UserEventContext,
    user_event_logger,
)
from api.database.models.event_types import EventCategory, EventType


class TestUserEventContext:
    """Tests for UserEventContext dataclass."""

    def test_create_minimal_context(self):
        """Create context with minimal required fields."""
        ctx = UserEventContext(
            event_type="page_view",
            event_category="navigation",
            session_id="abc123",
        )
        assert ctx.event_type == "page_view"
        assert ctx.event_category == "navigation"
        assert ctx.session_id == "abc123"
        assert ctx.user_id is None
        assert ctx.event_data is None

    def test_create_full_context(self):
        """Create context with all fields."""
        ctx = UserEventContext(
            event_type="poi_click",
            event_category="interaction",
            session_id="abc123",
            user_id="user-uuid",
            event_data={"poi_id": "poi-123"},
            device_type="mobile",
            os="iOS 17",
            browser="Safari 17",
            screen_width=390,
            screen_height=844,
            page_path="/map",
            referrer="https://google.com",
            latitude=-23.5,
            longitude=-46.6,
            duration_ms=1500,
            error_message=None,
        )
        assert ctx.event_type == "poi_click"
        assert ctx.user_id == "user-uuid"
        assert ctx.device_type == "mobile"
        assert ctx.screen_width == 390


class TestUserEventLogger:
    """Tests for UserEventLogger service."""

    def test_singleton_pattern(self):
        """Logger should be singleton."""
        logger1 = UserEventLogger()
        logger2 = UserEventLogger()
        assert logger1 is logger2

    @pytest.mark.asyncio
    async def test_log_event_queues_event(self):
        """log_event should queue the event."""
        logger = UserEventLogger()
        # Clear queue first
        logger._event_queue.clear()

        await logger.log_event(
            event_type="page_view",
            session_id="test-session",
            page_path="/map",
        )

        assert len(logger._event_queue) > 0
        # Clean up
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_event_auto_detects_category(self):
        """log_event should auto-detect category if not provided."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_event(
            event_type="login",
            session_id="test-session",
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_category == "auth"
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_event_uses_provided_category(self):
        """log_event should use provided category."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_event(
            event_type="custom_event",
            event_category="custom",
            session_id="test-session",
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_category == "custom"
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_event_truncates_error_message(self):
        """log_event should truncate long error messages."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        long_error = "x" * 2000
        await logger.log_event(
            event_type="api_error",
            session_id="test-session",
            error_message=long_error,
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert len(ctx.error_message) == 1000
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_events_batch(self):
        """log_events_batch should queue multiple events."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        events = [
            {"event_type": "page_view", "session_id": "s1", "page_path": "/map"},
            {"event_type": "poi_click", "session_id": "s1", "event_data": {"poi_id": "123"}},
            {"event_type": "login", "session_id": "s1", "user_id": "user-1"},
        ]
        await logger.log_events_batch(events)

        assert len(logger._event_queue) == 3
        logger._event_queue.clear()


class TestHelperMethods:
    """Tests for helper logging methods."""

    @pytest.mark.asyncio
    async def test_log_page_view(self):
        """log_page_view should create page_view event."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_page_view(
            session_id="test-session",
            page_path="/map",
            referrer="https://google.com",
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_type == "page_view"
        assert ctx.event_category == "navigation"
        assert ctx.page_path == "/map"
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_login(self):
        """log_login should create login event."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_login(
            session_id="test-session",
            user_id="user-123",
            device_type="mobile",
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_type == "login"
        assert ctx.event_category == "auth"
        assert ctx.user_id == "user-123"
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_logout(self):
        """log_logout should create logout event."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_logout(
            session_id="test-session",
            user_id="user-123",
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_type == "logout"
        assert ctx.event_category == "auth"
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_error(self):
        """log_error should create error event."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_error(
            session_id="test-session",
            event_type="api_error",
            error_message="Connection failed",
            page_path="/search",
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_type == "api_error"
        assert ctx.event_category == "error"
        assert ctx.error_message == "Connection failed"
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_performance(self):
        """log_performance should create performance event."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_performance(
            session_id="test-session",
            event_type="map_load_time",
            duration_ms=1500,
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_type == "map_load_time"
        assert ctx.event_category == "performance"
        assert ctx.duration_ms == 1500
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_map_event(self):
        """log_map_event should create map management event."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_map_event(
            session_id="test-session",
            event_type="map_create",
            event_data={"map_id": "map-123"},
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_type == "map_create"
        assert ctx.event_category == "map_management"
        logger._event_queue.clear()

    @pytest.mark.asyncio
    async def test_log_conversion(self):
        """log_conversion should create conversion event."""
        logger = UserEventLogger()
        logger._event_queue.clear()

        await logger.log_conversion(
            session_id="test-session",
            event_type="search_started",
            event_data={"query": "São Paulo"},
        )

        assert len(logger._event_queue) == 1
        ctx = logger._event_queue[0]
        assert ctx.event_type == "search_started"
        assert ctx.event_category == "conversion"
        logger._event_queue.clear()


class TestEventTypes:
    """Tests for event type to category mapping."""

    def test_auth_events(self):
        """Auth events should map to auth category."""
        from api.database.models.event_types import get_category_for_event_type

        assert get_category_for_event_type("login") == "auth"
        assert get_category_for_event_type("logout") == "auth"

    def test_navigation_events(self):
        """Navigation events should map to navigation category."""
        from api.database.models.event_types import get_category_for_event_type

        assert get_category_for_event_type("page_view") == "navigation"
        assert get_category_for_event_type("linear_map_view") == "navigation"
        assert get_category_for_event_type("osm_map_view") == "navigation"

    def test_map_management_events(self):
        """Map management events should map to map_management category."""
        from api.database.models.event_types import get_category_for_event_type

        assert get_category_for_event_type("map_create") == "map_management"
        assert get_category_for_event_type("map_adopt") == "map_management"
        assert get_category_for_event_type("map_remove") == "map_management"
        assert get_category_for_event_type("map_export_pdf") == "map_management"

    def test_error_events(self):
        """Error events should map to error category."""
        from api.database.models.event_types import get_category_for_event_type

        assert get_category_for_event_type("api_error") == "error"
        assert get_category_for_event_type("geolocation_error") == "error"

    def test_performance_events(self):
        """Performance events should map to performance category."""
        from api.database.models.event_types import get_category_for_event_type

        assert get_category_for_event_type("map_load_time") == "performance"
        assert get_category_for_event_type("search_response_time") == "performance"

    def test_conversion_events(self):
        """Conversion events should map to conversion category."""
        from api.database.models.event_types import get_category_for_event_type

        assert get_category_for_event_type("search_started") == "conversion"
        assert get_category_for_event_type("search_completed") == "conversion"
        assert get_category_for_event_type("search_abandoned") == "conversion"

    def test_unknown_event(self):
        """Unknown events should return None."""
        from api.database.models.event_types import get_category_for_event_type

        assert get_category_for_event_type("unknown_event") is None
        assert get_category_for_event_type("custom_event") is None
