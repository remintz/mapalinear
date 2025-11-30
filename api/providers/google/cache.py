"""
Cache for Google Places API data.

Follows Google TOS:
- place_id can be stored permanently
- rating data must be refreshed every 30 days
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg

from .client import GooglePlaceResult

logger = logging.getLogger(__name__)

# Cache TTL for rating data (per Google TOS)
RATING_CACHE_TTL_DAYS = 30


class GooglePlacesCache:
    """
    Cache for Google Places data in PostgreSQL.

    Stores place_id permanently and rating data for up to 30 days.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "mapalinear",
        user: str = "mapalinear",
        password: str = "mapalinear",
    ):
        """Initialize cache configuration."""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10,
            )
        return self._pool

    async def initialize(self):
        """Initialize the cache table if it doesn't exist."""
        pool = await self._get_pool()

        # Read and execute schema
        schema_sql = """
        CREATE TABLE IF NOT EXISTS google_places_cache (
            osm_poi_id VARCHAR(100) PRIMARY KEY,
            google_place_id VARCHAR(200) NOT NULL,
            rating DECIMAL(2,1),
            user_rating_count INTEGER,
            google_maps_uri TEXT,
            matched_name VARCHAR(500),
            match_distance_meters DECIMAL(10,2),
            search_latitude DECIMAL(10,7) NOT NULL,
            search_longitude DECIMAL(10,7) NOT NULL,
            search_name VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT valid_rating CHECK (rating IS NULL OR (rating >= 1.0 AND rating <= 5.0)),
            CONSTRAINT valid_review_count CHECK (user_rating_count IS NULL OR user_rating_count >= 0)
        );

        CREATE INDEX IF NOT EXISTS idx_google_places_expires
            ON google_places_cache(expires_at);

        CREATE INDEX IF NOT EXISTS idx_google_places_google_id
            ON google_places_cache(google_place_id);
        """

        async with pool.acquire() as conn:
            await conn.execute(schema_sql)

        logger.info("Google Places cache initialized")

    async def get(self, osm_poi_id: str) -> Optional[GooglePlaceResult]:
        """
        Get cached rating data for a POI.

        Args:
            osm_poi_id: The OSM POI ID

        Returns:
            GooglePlaceResult if found and not expired, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT google_place_id, rating, user_rating_count, google_maps_uri,
                       matched_name, match_distance_meters
                FROM google_places_cache
                WHERE osm_poi_id = $1 AND expires_at > NOW()
                """,
                osm_poi_id,
            )

            if row:
                logger.debug(f"Cache HIT for POI {osm_poi_id}")
                return GooglePlaceResult(
                    place_id=row["google_place_id"],
                    name=row["matched_name"] or "",
                    rating=float(row["rating"]) if row["rating"] else None,
                    user_rating_count=row["user_rating_count"],
                    google_maps_uri=row["google_maps_uri"],
                    distance_meters=(
                        float(row["match_distance_meters"])
                        if row["match_distance_meters"]
                        else None
                    ),
                )

            logger.debug(f"Cache MISS for POI {osm_poi_id}")
            return None

    async def set(
        self,
        osm_poi_id: str,
        result: GooglePlaceResult,
        search_latitude: float,
        search_longitude: float,
        search_name: str,
    ):
        """
        Store rating data in cache.

        Args:
            osm_poi_id: The OSM POI ID
            result: The Google Places result to cache
            search_latitude: Latitude used in search
            search_longitude: Longitude used in search
            search_name: Name used in search
        """
        pool = await self._get_pool()
        expires_at = datetime.now(timezone.utc) + timedelta(days=RATING_CACHE_TTL_DAYS)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO google_places_cache (
                    osm_poi_id, google_place_id, rating, user_rating_count,
                    google_maps_uri, matched_name, match_distance_meters,
                    search_latitude, search_longitude, search_name, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (osm_poi_id) DO UPDATE SET
                    google_place_id = EXCLUDED.google_place_id,
                    rating = EXCLUDED.rating,
                    user_rating_count = EXCLUDED.user_rating_count,
                    google_maps_uri = EXCLUDED.google_maps_uri,
                    matched_name = EXCLUDED.matched_name,
                    match_distance_meters = EXCLUDED.match_distance_meters,
                    search_latitude = EXCLUDED.search_latitude,
                    search_longitude = EXCLUDED.search_longitude,
                    search_name = EXCLUDED.search_name,
                    created_at = NOW(),
                    expires_at = EXCLUDED.expires_at
                """,
                osm_poi_id,
                result.place_id,
                result.rating,
                result.user_rating_count,
                result.google_maps_uri,
                result.name,
                result.distance_meters,
                search_latitude,
                search_longitude,
                search_name,
                expires_at,
            )

        logger.debug(f"Cached Google Places data for POI {osm_poi_id}")

    async def set_not_found(
        self,
        osm_poi_id: str,
        search_latitude: float,
        search_longitude: float,
        search_name: str,
    ):
        """
        Store a "not found" marker to avoid repeated API calls.

        Uses a shorter TTL (7 days) for not-found entries.
        """
        pool = await self._get_pool()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO google_places_cache (
                    osm_poi_id, google_place_id, search_latitude, search_longitude,
                    search_name, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (osm_poi_id) DO UPDATE SET
                    google_place_id = EXCLUDED.google_place_id,
                    rating = NULL,
                    user_rating_count = NULL,
                    google_maps_uri = NULL,
                    matched_name = NULL,
                    search_latitude = EXCLUDED.search_latitude,
                    search_longitude = EXCLUDED.search_longitude,
                    search_name = EXCLUDED.search_name,
                    created_at = NOW(),
                    expires_at = EXCLUDED.expires_at
                """,
                osm_poi_id,
                "__NOT_FOUND__",  # Special marker
                search_latitude,
                search_longitude,
                search_name,
                expires_at,
            )

        logger.debug(f"Cached NOT_FOUND for POI {osm_poi_id}")

    async def is_not_found(self, osm_poi_id: str) -> bool:
        """Check if a POI was previously searched and not found."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT google_place_id
                FROM google_places_cache
                WHERE osm_poi_id = $1 AND expires_at > NOW()
                """,
                osm_poi_id,
            )

            return row is not None and row["google_place_id"] == "__NOT_FOUND__"

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM google_places_cache WHERE expires_at < NOW()"
            )
            # Parse "DELETE X" to get count
            count = int(result.split()[-1]) if result else 0

        logger.info(f"Cleaned up {count} expired Google Places cache entries")
        return count

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE google_place_id != '__NOT_FOUND__') as with_data,
                    COUNT(*) FILTER (WHERE google_place_id = '__NOT_FOUND__') as not_found,
                    COUNT(*) FILTER (WHERE rating IS NOT NULL) as with_rating,
                    AVG(rating) FILTER (WHERE rating IS NOT NULL) as avg_rating,
                    COUNT(*) FILTER (WHERE expires_at < NOW()) as expired
                FROM google_places_cache
                """
            )

            return {
                "total_entries": row["total"],
                "with_data": row["with_data"],
                "not_found": row["not_found"],
                "with_rating": row["with_rating"],
                "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else None,
                "expired": row["expired"],
            }

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
