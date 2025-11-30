"""
Service for enriching POIs with Google Places ratings.

Orchestrates cache lookups and API calls to efficiently
fetch ratings for multiple POIs.
"""

import asyncio
import logging
import os
from typing import List, Optional, Callable

from api.models.road_models import RoadMilestone

from .cache import GooglePlacesCache
from .client import GooglePlacesClient

logger = logging.getLogger(__name__)


class GooglePlacesService:
    """
    Service for enriching POIs with Google Places ratings.

    Uses caching to minimize API calls and costs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[GooglePlacesCache] = None,
        search_radius_meters: float = 200.0,
    ):
        """
        Initialize the service.

        Args:
            api_key: Google Places API key (falls back to env var)
            cache: Optional cache instance (creates default if not provided)
            search_radius_meters: Radius to search for places
        """
        self.api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        self.search_radius_meters = search_radius_meters
        self._cache = cache
        self._client: Optional[GooglePlacesClient] = None
        self._initialized = False

    @property
    def is_configured(self) -> bool:
        """Check if the service has a valid API key."""
        return bool(self.api_key)

    async def initialize(self):
        """Initialize cache and client."""
        if self._initialized:
            return

        if not self.is_configured:
            logger.warning(
                "Google Places API key not configured. "
                "Set GOOGLE_PLACES_API_KEY environment variable to enable ratings."
            )
            return

        # Initialize cache
        if self._cache is None:
            self._cache = GooglePlacesCache(
                host=os.environ.get("POSTGRES_HOST", "localhost"),
                port=int(os.environ.get("POSTGRES_PORT", "5432")),
                database=os.environ.get("POSTGRES_DATABASE", "mapalinear"),
                user=os.environ.get("POSTGRES_USER", "mapalinear"),
                password=os.environ.get("POSTGRES_PASSWORD", "mapalinear"),
            )

        await self._cache.initialize()

        # Initialize client
        self._client = GooglePlacesClient(
            api_key=self.api_key,
            rate_limit_delay=0.1,  # 100ms between requests
        )

        self._initialized = True
        logger.info("Google Places service initialized")

    async def enrich_milestone(
        self, milestone: RoadMilestone
    ) -> RoadMilestone:
        """
        Enrich a single milestone with Google Places rating.

        Args:
            milestone: The milestone to enrich

        Returns:
            The milestone with Google Places data added (if found)
        """
        if not self.is_configured or not self._initialized:
            return milestone

        poi_id = milestone.id
        lat = milestone.coordinates.latitude
        lng = milestone.coordinates.longitude
        name = milestone.name

        # Check cache first
        cached = await self._cache.get(poi_id)
        if cached:
            milestone.google_place_id = cached.place_id
            milestone.google_rating = cached.rating
            milestone.google_review_count = cached.user_rating_count
            milestone.google_maps_url = cached.google_maps_uri
            return milestone

        # Check if previously searched and not found
        if await self._cache.is_not_found(poi_id):
            return milestone

        # Search Google Places API
        result = await self._client.search_nearby(
            latitude=lat,
            longitude=lng,
            name=name,
            radius_meters=self.search_radius_meters,
        )

        if result:
            # Cache the result
            await self._cache.set(
                osm_poi_id=poi_id,
                result=result,
                search_latitude=lat,
                search_longitude=lng,
                search_name=name,
            )

            # Update milestone
            milestone.google_place_id = result.place_id
            milestone.google_rating = result.rating
            milestone.google_review_count = result.user_rating_count
            milestone.google_maps_url = result.google_maps_uri
        else:
            # Cache the "not found" result
            await self._cache.set_not_found(
                osm_poi_id=poi_id,
                search_latitude=lat,
                search_longitude=lng,
                search_name=name,
            )

        return milestone

    async def enrich_milestones(
        self,
        milestones: List[RoadMilestone],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[RoadMilestone]:
        """
        Enrich multiple milestones with Google Places ratings.

        Args:
            milestones: List of milestones to enrich
            progress_callback: Optional callback(current, total) for progress

        Returns:
            List of enriched milestones
        """
        if not self.is_configured:
            logger.warning("Google Places not configured, skipping enrichment")
            return milestones

        await self.initialize()

        total = len(milestones)
        enriched = []

        # Process milestones with rate limiting
        for i, milestone in enumerate(milestones):
            try:
                enriched_milestone = await self.enrich_milestone(milestone)
                enriched.append(enriched_milestone)
            except Exception as e:
                logger.error(f"Error enriching milestone {milestone.id}: {e}")
                enriched.append(milestone)  # Keep original on error

            if progress_callback:
                progress_callback(i + 1, total)

        # Log summary
        with_rating = sum(1 for m in enriched if m.google_rating is not None)
        logger.info(
            f"Enriched {total} milestones: {with_rating} with ratings "
            f"({with_rating * 100 / total:.1f}%)"
        )

        return enriched

    async def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        if not self._cache:
            return {"error": "Cache not initialized"}

        return await self._cache.get_stats()

    async def close(self):
        """Close client and cache connections."""
        if self._client:
            await self._client.close()
            self._client = None

        if self._cache:
            await self._cache.close()
            self._cache = None

        self._initialized = False


# Singleton instance
_service_instance: Optional[GooglePlacesService] = None


def get_google_places_service() -> GooglePlacesService:
    """Get or create the Google Places service singleton."""
    global _service_instance

    if _service_instance is None:
        _service_instance = GooglePlacesService()

    return _service_instance


async def enrich_milestones_with_ratings(
    milestones: List[RoadMilestone],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[RoadMilestone]:
    """
    Convenience function to enrich milestones with Google Places ratings.

    Args:
        milestones: List of milestones to enrich
        progress_callback: Optional callback for progress updates

    Returns:
        List of enriched milestones
    """
    service = get_google_places_service()
    return await service.enrich_milestones(milestones, progress_callback)
