"""
Repository for user event analytics.
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def utcnow() -> datetime:
    """Return current UTC time as naive datetime (for database compatibility)."""
    return datetime.utcnow()

from sqlalchemy import delete, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.user_event import UserEvent
from api.database.repositories.base import BaseRepository


class UserEventRepository(BaseRepository[UserEvent]):
    """Repository for managing user events."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, UserEvent)

    async def create_event(
        self,
        event_type: str,
        event_category: str,
        session_id: str,
        user_id: Optional[str] = None,
        event_data: Optional[dict] = None,
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
    ) -> UserEvent:
        """
        Create a new user event.

        Args:
            event_type: Type of event (e.g., "login", "page_view")
            event_category: Category of event (e.g., "auth", "navigation")
            session_id: Browser session ID
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

        Returns:
            Created UserEvent instance
        """
        event = UserEvent(
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
            error_message=error_message,
        )
        return await self.create(event)

    async def create_events_batch(self, events: List[Dict[str, Any]]) -> int:
        """
        Create multiple events in batch.

        Args:
            events: List of event dictionaries

        Returns:
            Number of events created
        """
        created = 0
        for event_data in events:
            event = UserEvent(**event_data)
            self.session.add(event)
            created += 1
        await self.session.flush()
        return created

    async def get_stats_by_event_type(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get aggregated statistics by event type.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with event type stats
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        result = await self.session.execute(
            select(
                UserEvent.event_category,
                UserEvent.event_type,
                func.count(UserEvent.id).label("count"),
                func.count(distinct(UserEvent.session_id)).label("unique_sessions"),
                func.count(distinct(UserEvent.user_id)).label("unique_users"),
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .group_by(UserEvent.event_category, UserEvent.event_type)
            .order_by(func.count(UserEvent.id).desc())
        )

        return [
            {
                "event_category": row.event_category,
                "event_type": row.event_type,
                "count": row.count,
                "unique_sessions": row.unique_sessions,
                "unique_users": row.unique_users or 0,
            }
            for row in result.all()
        ]

    async def get_stats_by_device(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get aggregated statistics by device type.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with device stats
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        result = await self.session.execute(
            select(
                UserEvent.device_type,
                UserEvent.os,
                UserEvent.browser,
                func.count(UserEvent.id).label("count"),
                func.count(distinct(UserEvent.session_id)).label("unique_sessions"),
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .where(UserEvent.device_type.isnot(None))
            .group_by(UserEvent.device_type, UserEvent.os, UserEvent.browser)
            .order_by(func.count(UserEvent.id).desc())
        )

        return [
            {
                "device_type": row.device_type,
                "os": row.os,
                "browser": row.browser,
                "count": row.count,
                "unique_sessions": row.unique_sessions,
            }
            for row in result.all()
        ]

    async def get_daily_active_users(
        self,
        days: int = 30,
    ) -> List[Dict]:
        """
        Get daily active users (DAU) count.

        Args:
            days: Number of days to look back

        Returns:
            List of dictionaries with daily active user counts
        """
        start_date = utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(
                func.date(UserEvent.created_at).label("date"),
                func.count(distinct(UserEvent.session_id)).label("unique_sessions"),
                func.count(distinct(UserEvent.user_id)).label("unique_users"),
                func.count(UserEvent.id).label("total_events"),
            )
            .where(UserEvent.created_at >= start_date)
            .group_by(func.date(UserEvent.created_at))
            .order_by(func.date(UserEvent.created_at).desc())
        )

        return [
            {
                "date": str(row.date),
                "unique_sessions": row.unique_sessions,
                "unique_users": row.unique_users or 0,
                "total_events": row.total_events,
            }
            for row in result.all()
        ]

    async def get_user_journey(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[UserEvent]:
        """
        Get all events for a specific session (user journey).

        Args:
            session_id: Session UUID
            limit: Maximum number of events to return

        Returns:
            List of UserEvent instances ordered by time
        """
        result = await self.session.execute(
            select(UserEvent)
            .where(UserEvent.session_id == session_id)
            .order_by(UserEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_feature_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get feature usage statistics.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with feature usage stats
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        # Focus on key features: map creation, search, export, tracking
        feature_events = [
            "map_create",
            "map_adopt",
            "map_remove",
            "search_started",
            "search_completed",
            "map_export_pdf",
            "map_export_geojson",
            "map_export_gpx",
            "route_tracking_start",
            "route_tracking_stop",
            "poi_click",
            "poi_filter_toggle",
        ]

        result = await self.session.execute(
            select(
                UserEvent.event_type,
                func.count(UserEvent.id).label("count"),
                func.count(distinct(UserEvent.session_id)).label("unique_sessions"),
                func.count(distinct(UserEvent.user_id)).label("unique_users"),
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .where(UserEvent.event_type.in_(feature_events))
            .group_by(UserEvent.event_type)
            .order_by(func.count(UserEvent.id).desc())
        )

        return [
            {
                "feature": row.event_type,
                "count": row.count,
                "unique_sessions": row.unique_sessions,
                "unique_users": row.unique_users or 0,
            }
            for row in result.all()
        ]

    async def get_poi_filter_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get POI filter toggle usage.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with filter usage stats
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        # Define JSONB accessor expressions as variables to ensure consistency
        # between SELECT and GROUP BY clauses
        filter_name_col = UserEvent.event_data["filter_name"].astext
        enabled_col = UserEvent.event_data["enabled"].astext

        result = await self.session.execute(
            select(
                filter_name_col.label("filter_name"),
                enabled_col.label("enabled"),
                func.count(UserEvent.id).label("count"),
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .where(UserEvent.event_type == "poi_filter_toggle")
            .group_by(filter_name_col, enabled_col)
            .order_by(func.count(UserEvent.id).desc())
        )

        return [
            {
                "filter_name": row.filter_name,
                "enabled": row.enabled == "true",
                "count": row.count,
            }
            for row in result.all()
        ]

    async def get_conversion_funnel(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        Get conversion funnel statistics.

        Funnel stages:
        1. Search started
        2. Search completed
        3. Map created/adopted

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            Dictionary with funnel stats
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        # Get counts for each funnel stage
        stages = ["search_started", "search_completed", "map_create", "map_adopt"]
        funnel = {}

        for stage in stages:
            result = await self.session.execute(
                select(
                    func.count(distinct(UserEvent.session_id)).label("sessions"),
                    func.count(UserEvent.id).label("events"),
                )
                .where(UserEvent.created_at >= start_date)
                .where(UserEvent.created_at <= end_date)
                .where(UserEvent.event_type == stage)
            )
            row = result.one()
            funnel[stage] = {
                "sessions": row.sessions,
                "events": row.events,
            }

        # Also get abandoned searches
        result = await self.session.execute(
            select(
                func.count(distinct(UserEvent.session_id)).label("sessions"),
                func.count(UserEvent.id).label("events"),
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .where(UserEvent.event_type == "search_abandoned")
        )
        row = result.one()
        funnel["search_abandoned"] = {
            "sessions": row.sessions,
            "events": row.events,
        }

        # Calculate conversion rates
        if funnel["search_started"]["sessions"] > 0:
            funnel["completion_rate"] = round(
                funnel["search_completed"]["sessions"]
                / funnel["search_started"]["sessions"]
                * 100,
                1,
            )
            funnel["abandonment_rate"] = round(
                funnel["search_abandoned"]["sessions"]
                / funnel["search_started"]["sessions"]
                * 100,
                1,
            )
            funnel["map_creation_rate"] = round(
                (funnel["map_create"]["sessions"] + funnel["map_adopt"]["sessions"])
                / funnel["search_started"]["sessions"]
                * 100,
                1,
            )
        else:
            funnel["completion_rate"] = 0
            funnel["abandonment_rate"] = 0
            funnel["map_creation_rate"] = 0

        return funnel

    async def get_performance_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get performance event statistics.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with performance stats
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        result = await self.session.execute(
            select(
                UserEvent.event_type,
                func.count(UserEvent.id).label("count"),
                func.avg(UserEvent.duration_ms).label("avg_duration_ms"),
                func.min(UserEvent.duration_ms).label("min_duration_ms"),
                func.max(UserEvent.duration_ms).label("max_duration_ms"),
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .where(UserEvent.event_category == "performance")
            .where(UserEvent.duration_ms.isnot(None))
            .group_by(UserEvent.event_type)
            .order_by(func.count(UserEvent.id).desc())
        )

        return [
            {
                "event_type": row.event_type,
                "count": row.count,
                "avg_duration_ms": round(row.avg_duration_ms, 2) if row.avg_duration_ms else 0,
                "min_duration_ms": row.min_duration_ms or 0,
                "max_duration_ms": row.max_duration_ms or 0,
            }
            for row in result.all()
        ]

    async def get_overview_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        Get overview statistics.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            Dictionary with overview stats
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        result = await self.session.execute(
            select(
                func.count(UserEvent.id).label("total_events"),
                func.count(distinct(UserEvent.session_id)).label("unique_sessions"),
                func.count(distinct(UserEvent.user_id)).label("unique_users"),
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
        )
        row = result.one()

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_events": row.total_events,
            "unique_sessions": row.unique_sessions,
            "unique_users": row.unique_users or 0,
        }

    async def cleanup_old_events(self, days_to_keep: int = 365) -> int:
        """
        Remove events older than specified days.

        Args:
            days_to_keep: Number of days of events to keep (default: 365)

        Returns:
            Number of deleted records
        """
        cutoff_date = utcnow() - timedelta(days=days_to_keep)

        result = await self.session.execute(
            delete(UserEvent).where(UserEvent.created_at < cutoff_date)
        )
        return result.rowcount

    async def get_login_locations(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get login events with location data.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            List of dictionaries with login location data
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        result = await self.session.execute(
            select(
                UserEvent.latitude,
                UserEvent.longitude,
                UserEvent.user_id,
                UserEvent.device_type,
                UserEvent.created_at,
                UserEvent.event_data,
            )
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .where(UserEvent.event_type == "login")
            .where(UserEvent.latitude.isnot(None))
            .where(UserEvent.longitude.isnot(None))
            .order_by(UserEvent.created_at.desc())
        )

        return [
            {
                "latitude": row.latitude,
                "longitude": row.longitude,
                "user_id": row.user_id,
                "device_type": row.device_type,
                "created_at": row.created_at.isoformat(),
                "user_email": row.event_data.get("user_email") if row.event_data else None,
                "user_name": row.event_data.get("user_name") if row.event_data else None,
            }
            for row in result.all()
        ]

    async def export_to_csv(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10000,
    ) -> str:
        """
        Export events to CSV format.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)
            limit: Maximum number of records to export

        Returns:
            CSV string
        """
        if start_date is None:
            start_date = utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = utcnow()

        result = await self.session.execute(
            select(UserEvent)
            .where(UserEvent.created_at >= start_date)
            .where(UserEvent.created_at <= end_date)
            .order_by(UserEvent.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "id",
                "created_at",
                "user_id",
                "session_id",
                "event_category",
                "event_type",
                "device_type",
                "os",
                "browser",
                "page_path",
                "duration_ms",
                "error_message",
            ]
        )

        # Data
        for event in events:
            writer.writerow(
                [
                    event.id,
                    event.created_at.isoformat(),
                    event.user_id or "",
                    event.session_id,
                    event.event_category,
                    event.event_type,
                    event.device_type or "",
                    event.os or "",
                    event.browser or "",
                    event.page_path or "",
                    event.duration_ms or "",
                    event.error_message or "",
                ]
            )

        return output.getvalue()
