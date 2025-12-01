"""
Repository for Google Places Cache operations.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.google_places_cache import GooglePlacesCache
from api.database.repositories.base import BaseRepository


class GooglePlacesCacheRepository(BaseRepository[GooglePlacesCache]):
    """Repository for Google Places cache operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, GooglePlacesCache)

    async def get_by_osm_id(self, osm_poi_id: str) -> Optional[GooglePlacesCache]:
        """
        Get cached Google Places data by OSM POI ID.

        Args:
            osm_poi_id: OSM POI identifier

        Returns:
            Cached entry if found and not expired, None otherwise
        """
        query = select(GooglePlacesCache).where(
            GooglePlacesCache.osm_poi_id == osm_poi_id,
            GooglePlacesCache.expires_at > datetime.now(timezone.utc),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_osm_id_include_expired(
        self, osm_poi_id: str
    ) -> Optional[GooglePlacesCache]:
        """
        Get cached entry by OSM POI ID, including expired entries.

        Args:
            osm_poi_id: OSM POI identifier

        Returns:
            Cached entry if found (may be expired), None otherwise
        """
        query = select(GooglePlacesCache).where(
            GooglePlacesCache.osm_poi_id == osm_poi_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        osm_poi_id: str,
        google_place_id: str,
        rating: Optional[float],
        user_rating_count: Optional[int],
        google_maps_uri: Optional[str],
        matched_name: Optional[str],
        match_distance_meters: Optional[float],
        search_latitude: float,
        search_longitude: float,
        search_name: Optional[str],
        ttl_seconds: int = 604800,  # 7 days default
    ) -> GooglePlacesCache:
        """
        Insert or update a Google Places cache entry.

        Args:
            osm_poi_id: OSM POI identifier
            google_place_id: Google Place ID
            rating: Rating (1.0-5.0)
            user_rating_count: Number of reviews
            google_maps_uri: Google Maps URL
            matched_name: Name matched from Google
            match_distance_meters: Distance between OSM and Google location
            search_latitude: Latitude used for search
            search_longitude: Longitude used for search
            search_name: Name used for search
            ttl_seconds: Time to live in seconds

        Returns:
            Created or updated cache entry
        """
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        # Check if entry exists
        existing = await self.get_by_osm_id_include_expired(osm_poi_id)

        if existing:
            # Update existing entry
            existing.google_place_id = google_place_id
            existing.rating = Decimal(str(rating)) if rating is not None else None
            existing.user_rating_count = user_rating_count
            existing.google_maps_uri = google_maps_uri
            existing.matched_name = matched_name
            existing.match_distance_meters = (
                Decimal(str(match_distance_meters))
                if match_distance_meters is not None
                else None
            )
            existing.search_latitude = Decimal(str(search_latitude))
            existing.search_longitude = Decimal(str(search_longitude))
            existing.search_name = search_name
            existing.expires_at = expires_at
            await self.session.flush()
            return existing
        else:
            # Create new entry
            entry = GooglePlacesCache(
                osm_poi_id=osm_poi_id,
                google_place_id=google_place_id,
                rating=Decimal(str(rating)) if rating is not None else None,
                user_rating_count=user_rating_count,
                google_maps_uri=google_maps_uri,
                matched_name=matched_name,
                match_distance_meters=(
                    Decimal(str(match_distance_meters))
                    if match_distance_meters is not None
                    else None
                ),
                search_latitude=Decimal(str(search_latitude)),
                search_longitude=Decimal(str(search_longitude)),
                search_name=search_name,
                expires_at=expires_at,
            )
            self.session.add(entry)
            await self.session.flush()
            return entry

    async def delete_expired(self) -> int:
        """
        Delete all expired cache entries.

        Returns:
            Number of deleted entries
        """
        query = delete(GooglePlacesCache).where(
            GooglePlacesCache.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.session.execute(query)
        return result.rowcount

    async def count_entries(self) -> int:
        """
        Count total cache entries.

        Returns:
            Total number of entries
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(GooglePlacesCache)
        result = await self.session.execute(query)
        return result.scalar_one()
