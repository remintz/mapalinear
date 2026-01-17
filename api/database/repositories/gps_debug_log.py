"""
Repository for GPS debug logs.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.gps_debug_log import GPSDebugLog
from api.database.repositories.base import BaseRepository


class GPSDebugLogRepository(BaseRepository[GPSDebugLog]):
    """Repository for managing GPS debug logs."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, GPSDebugLog)

    async def create_log(
        self,
        user_id: str,
        user_email: str,
        map_id: str,
        map_origin: str,
        map_destination: str,
        latitude: float,
        longitude: float,
        gps_accuracy: Optional[float] = None,
        distance_from_origin_km: Optional[float] = None,
        is_on_route: bool = False,
        distance_to_route_m: Optional[float] = None,
        previous_pois: Optional[list] = None,
        next_pois: Optional[list] = None,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> GPSDebugLog:
        """
        Create a new GPS debug log entry.

        Args:
            user_id: Admin user ID
            user_email: Admin user email
            map_id: Map being viewed
            map_origin: Map origin city
            map_destination: Map destination city
            latitude: GPS latitude
            longitude: GPS longitude
            gps_accuracy: GPS accuracy in meters
            distance_from_origin_km: Calculated distance from route origin
            is_on_route: Whether user is considered on route
            distance_to_route_m: Distance to nearest point on route in meters
            previous_pois: List of 2 previous POIs with distances
            next_pois: List of 5 next POIs with distances
            session_id: Frontend session ID
            user_agent: Browser/device info

        Returns:
            Created GPSDebugLog instance
        """
        log = GPSDebugLog(
            user_id=user_id,
            user_email=user_email,
            map_id=map_id,
            map_origin=map_origin,
            map_destination=map_destination,
            latitude=latitude,
            longitude=longitude,
            gps_accuracy=gps_accuracy,
            distance_from_origin_km=distance_from_origin_km,
            is_on_route=is_on_route,
            distance_to_route_m=distance_to_route_m,
            previous_pois=previous_pois,
            next_pois=next_pois,
            session_id=session_id,
            user_agent=user_agent,
        )
        return await self.create(log)

    async def get_last_log_for_user_map(
        self,
        user_id: str,
        map_id: str,
    ) -> Optional[GPSDebugLog]:
        """
        Get the most recent log for a user and map combination.

        Used to check if enough time has passed since last log (5 min throttle).

        Args:
            user_id: Admin user ID
            map_id: Map ID

        Returns:
            Most recent GPSDebugLog or None
        """
        result = await self.session.execute(
            select(GPSDebugLog)
            .where(GPSDebugLog.user_id == user_id)
            .where(GPSDebugLog.map_id == map_id)
            .order_by(GPSDebugLog.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_logs_by_map(
        self,
        map_id: str,
        limit: int = 100,
    ) -> List[GPSDebugLog]:
        """
        Get all debug logs for a specific map.

        Args:
            map_id: Map ID
            limit: Maximum number of records to return

        Returns:
            List of GPSDebugLog instances
        """
        result = await self.session.execute(
            select(GPSDebugLog)
            .where(GPSDebugLog.map_id == map_id)
            .order_by(GPSDebugLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_logs_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[GPSDebugLog]:
        """
        Get all debug logs for a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of records to return

        Returns:
            List of GPSDebugLog instances
        """
        result = await self.session.execute(
            select(GPSDebugLog)
            .where(GPSDebugLog.user_id == user_id)
            .order_by(GPSDebugLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_logs(
        self,
        limit: int = 100,
    ) -> List[GPSDebugLog]:
        """
        Get the most recent GPS debug logs.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of GPSDebugLog instances
        """
        result = await self.session.execute(
            select(GPSDebugLog)
            .order_by(GPSDebugLog.created_at.desc())
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
            delete(GPSDebugLog).where(GPSDebugLog.created_at < cutoff_date)
        )
        return result.rowcount
