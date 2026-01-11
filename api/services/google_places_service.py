"""
Service for enriching POIs with Google Places data (ratings, reviews, URLs).

This service queries the Google Places API to fetch ratings and review counts
for restaurants and hotels, caching results to minimize API calls.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.repositories.google_places_cache import GooglePlacesCacheRepository
from api.models.road_models import MilestoneType, RoadMilestone
from api.providers.settings import get_settings
from api.services.api_call_logger import api_call_logger

logger = logging.getLogger(__name__)


@dataclass
class GooglePlaceData:
    """Data returned from Google Places API."""

    google_place_id: str
    rating: Optional[float]
    rating_count: Optional[int]
    google_maps_uri: Optional[str]
    matched_name: Optional[str]
    match_distance_meters: Optional[float]


# Types that should be enriched with Google Places data
ENRICHABLE_TYPES = {
    MilestoneType.RESTAURANT,
    MilestoneType.FAST_FOOD,
    MilestoneType.CAFE,
    MilestoneType.BAR,
    MilestoneType.PUB,
    MilestoneType.BAKERY,
    MilestoneType.HOTEL,
}


class GooglePlacesService:
    """Service for fetching and caching Google Places data."""

    # Google Places API endpoint
    NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize the service.

        Args:
            session: SQLAlchemy async session for cache operations.
                     If None, cache will not be used.
        """
        self.settings = get_settings()
        self.session = session
        self.cache_repo = (
            GooglePlacesCacheRepository(session) if session else None
        )

    def is_enabled(self) -> bool:
        """Check if Google Places enrichment is enabled and configured."""
        return (
            self.settings.google_places_enabled
            and self.settings.google_places_api_key is not None
        )

    def should_enrich(self, milestone: RoadMilestone) -> bool:
        """Check if a milestone should be enriched with Google Places data."""
        return milestone.type in ENRICHABLE_TYPES

    async def get_place_data(
        self,
        osm_poi_id: str,
        name: str,
        latitude: float,
        longitude: float,
        poi_type: MilestoneType,
    ) -> Optional[GooglePlaceData]:
        """
        Get Google Places data for a POI.

        First checks the cache, then queries the API if needed.

        Args:
            osm_poi_id: OSM POI identifier (for caching)
            name: POI name to search for
            latitude: POI latitude
            longitude: POI longitude
            poi_type: Type of POI

        Returns:
            GooglePlaceData if found, None otherwise
        """
        if not self.is_enabled():
            return None

        # Check cache first
        if self.cache_repo:
            cached = await self.cache_repo.get_by_osm_id(osm_poi_id)
            if cached:
                return GooglePlaceData(
                    google_place_id=cached.google_place_id,
                    rating=float(cached.rating) if cached.rating else None,
                    rating_count=cached.user_rating_count,
                    google_maps_uri=cached.google_maps_uri,
                    matched_name=cached.matched_name,
                    match_distance_meters=(
                        float(cached.match_distance_meters)
                        if cached.match_distance_meters
                        else None
                    ),
                )

        # Query Google Places API
        try:
            place_data = await self._search_nearby(
                name=name,
                latitude=latitude,
                longitude=longitude,
                poi_type=poi_type,
            )

            if place_data and self.cache_repo:
                # Cache the result
                await self.cache_repo.upsert(
                    osm_poi_id=osm_poi_id,
                    google_place_id=place_data.google_place_id,
                    rating=place_data.rating,
                    user_rating_count=place_data.rating_count,
                    google_maps_uri=place_data.google_maps_uri,
                    matched_name=place_data.matched_name,
                    match_distance_meters=place_data.match_distance_meters,
                    search_latitude=latitude,
                    search_longitude=longitude,
                    search_name=name,
                    ttl_seconds=self.settings.google_places_cache_ttl,
                )
                logger.debug(f"Cached Google Places data for POI {osm_poi_id}")

            return place_data

        except Exception as e:
            logger.error(f"Error fetching Google Places data for {name}: {e}")
            return None

    async def _search_nearby(
        self,
        name: str,
        latitude: float,
        longitude: float,
        poi_type: MilestoneType,
    ) -> Optional[GooglePlaceData]:
        """
        Search for a place using Google Places Nearby Search API.

        Args:
            name: Place name
            latitude: Search latitude
            longitude: Search longitude
            poi_type: Type of POI

        Returns:
            GooglePlaceData if found, None otherwise
        """
        # Map MilestoneType to Google Places types
        included_types = self._get_google_types(poi_type)

        request_body = {
            "includedTypes": included_types,
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": 100.0,  # 100 meters radius
                }
            },
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.settings.google_places_api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.rating,"
                "places.userRatingCount,places.googleMapsUri,places.location"
            ),
        }

        start_time = time.time()
        response_status = 0
        response_size = None
        error_msg = None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.NEARBY_SEARCH_URL,
                    json=request_body,
                    headers=headers,
                    timeout=10.0,
                )

                response_status = response.status_code
                response_size = len(response.content)

                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(
                        f"Google Places API error: {response.status_code} - {response.text}"
                    )
                    
                    # Log failed API call
                    duration_ms = int((time.time() - start_time) * 1000)
                    await api_call_logger.log_call(
                        provider="google_places",
                        operation="nearby_search",
                        endpoint=self.NEARBY_SEARCH_URL,
                        http_method="POST",
                        response_status=response_status,
                        duration_ms=duration_ms,
                        request_params={
                            "name": name,
                            "latitude": latitude,
                            "longitude": longitude,
                            "poi_type": poi_type.value if hasattr(poi_type, 'value') else str(poi_type),
                            "included_types": included_types,
                        },
                        response_size_bytes=response_size,
                        error_message=error_msg,
                    )
                    return None

                data = response.json()
                places = data.get("places", [])

                # Log successful API call
                duration_ms = int((time.time() - start_time) * 1000)
                await api_call_logger.log_call(
                    provider="google_places",
                    operation="nearby_search",
                    endpoint=self.NEARBY_SEARCH_URL,
                    http_method="POST",
                    response_status=response_status,
                    duration_ms=duration_ms,
                    request_params={
                        "name": name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "poi_type": poi_type.value if hasattr(poi_type, 'value') else str(poi_type),
                        "included_types": included_types,
                    },
                    response_size_bytes=response_size,
                    result_count=len(places),
                )

                if not places:
                    logger.debug(f"No Google Places results for {name}")
                    return None

                # Find the best match based on name similarity
                best_match = self._find_best_match(name, places, latitude, longitude)

                if best_match:
                    return GooglePlaceData(
                        google_place_id=best_match.get("id", ""),
                        rating=best_match.get("rating"),
                        rating_count=best_match.get("userRatingCount"),
                        google_maps_uri=best_match.get("googleMapsUri"),
                        matched_name=best_match.get("displayName", {}).get("text"),
                        match_distance_meters=self._calculate_distance(
                            latitude,
                            longitude,
                            best_match.get("location", {}).get("latitude", latitude),
                            best_match.get("location", {}).get("longitude", longitude),
                        ),
                    )

                return None

            except Exception as e:
                error_msg = str(e)[:500]
                logger.warning(f"Google Places API exception: {e}")
                
                # Log failed API call
                duration_ms = int((time.time() - start_time) * 1000)
                await api_call_logger.log_call(
                    provider="google_places",
                    operation="nearby_search",
                    endpoint=self.NEARBY_SEARCH_URL,
                    http_method="POST",
                    response_status=response_status or 500,
                    duration_ms=duration_ms,
                    request_params={
                        "name": name,
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    response_size_bytes=response_size,
                    error_message=error_msg,
                )
                return None

    def _get_google_types(self, poi_type: MilestoneType) -> List[str]:
        """Map MilestoneType to Google Places types."""
        type_mapping = {
            MilestoneType.RESTAURANT: ["restaurant"],
            MilestoneType.FAST_FOOD: ["fast_food_restaurant"],
            MilestoneType.CAFE: ["cafe", "coffee_shop"],
            MilestoneType.BAR: ["bar"],
            MilestoneType.PUB: ["bar"],
            MilestoneType.BAKERY: ["bakery"],
            MilestoneType.HOTEL: ["hotel", "lodging"],
        }
        return type_mapping.get(poi_type, ["restaurant"])

    def _find_best_match(
        self,
        search_name: str,
        places: List[dict],
        search_lat: float,
        search_lon: float,
    ) -> Optional[dict]:
        """
        Find the best matching place from search results.

        Uses a combination of name similarity and distance.
        """
        if not places:
            return None

        search_name_lower = search_name.lower().strip()
        best_score = -1
        best_place = None

        for place in places:
            place_name = place.get("displayName", {}).get("text", "").lower().strip()
            place_lat = place.get("location", {}).get("latitude", search_lat)
            place_lon = place.get("location", {}).get("longitude", search_lon)

            # Calculate name similarity (simple substring match)
            name_score = 0
            if search_name_lower in place_name or place_name in search_name_lower:
                name_score = 1.0
            else:
                # Check for partial word matches
                search_words = set(search_name_lower.split())
                place_words = set(place_name.split())
                common_words = search_words & place_words
                if common_words:
                    name_score = len(common_words) / max(
                        len(search_words), len(place_words)
                    )

            # Calculate distance penalty (closer is better)
            distance = self._calculate_distance(
                search_lat, search_lon, place_lat, place_lon
            )
            distance_score = max(0, 1 - distance / 200)  # Normalize to 200m

            # Combined score (name is more important)
            score = name_score * 0.7 + distance_score * 0.3

            if score > best_score:
                best_score = score
                best_place = place

        # Only return if score is reasonable
        if best_score > 0.2:
            return best_place

        # If no good match by name, return the closest one
        return places[0] if places else None

    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters (Haversine formula)."""
        import math

        R = 6371000  # Earth's radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
            delta_lambda / 2
        ) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    async def enrich_milestones(
        self, milestones: List[RoadMilestone]
    ) -> List[RoadMilestone]:
        """
        Enrich a list of milestones with Google Places data.

        Only enriches restaurants and hotels. Uses batch processing
        with rate limiting to avoid overwhelming the API.

        Args:
            milestones: List of milestones to enrich

        Returns:
            List of enriched milestones
        """
        if not self.is_enabled():
            logger.info("Google Places enrichment is disabled")
            return milestones

        enriched = []
        enrichable_count = 0

        for milestone in milestones:
            if self.should_enrich(milestone):
                enrichable_count += 1
                # Get OSM ID from tags
                osm_id = milestone.tags.get("osm_id") or milestone.tags.get("id")
                if osm_id and not isinstance(osm_id, str):
                    osm_id = str(osm_id)

                if osm_id:
                    place_data = await self.get_place_data(
                        osm_poi_id=osm_id,
                        name=milestone.name,
                        latitude=milestone.coordinates.latitude,
                        longitude=milestone.coordinates.longitude,
                        poi_type=milestone.type,
                    )

                    if place_data:
                        # Create a new milestone with enriched data
                        milestone_dict = milestone.model_dump()
                        milestone_dict["rating"] = place_data.rating
                        milestone_dict["rating_count"] = place_data.rating_count
                        milestone_dict["google_maps_uri"] = place_data.google_maps_uri
                        milestone = RoadMilestone(**milestone_dict)

                    # Rate limiting: small delay between API calls
                    await asyncio.sleep(0.1)

            enriched.append(milestone)

        logger.info(
            f"Enriched {enrichable_count} POIs with Google Places data "
            f"(out of {len(milestones)} total)"
        )
        return enriched


# Sync wrapper for use in non-async contexts
def enrich_milestones_sync(milestones: List[RoadMilestone]) -> List[RoadMilestone]:
    """
    Sync wrapper for enriching milestones with Google Places data.

    Creates a standalone database session for the operation.
    """
    from api.database.connection import get_database_url

    async def _enrich():
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        settings = get_settings()

        # Check if enrichment is enabled
        if not settings.google_places_enabled or not settings.google_places_api_key:
            logger.info("Google Places enrichment is disabled or not configured")
            return milestones

        # Create standalone engine
        engine = create_async_engine(
            get_database_url(),
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )

        session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        try:
            async with session_maker() as session:
                service = GooglePlacesService(session)
                result = await service.enrich_milestones(milestones)
                await session.commit()
                return result
        finally:
            await engine.dispose()

    return asyncio.run(_enrich())


async def enrich_map_pois_with_google_places(
    session: AsyncSession,
    map_id: str,
) -> int:
    """
    Enrich POIs in a map with Google Places data (ratings).

    This function fetches POIs for the given map from the database,
    enriches eligible POIs (restaurants, hotels, cafes, etc.) with
    Google Places ratings, and updates them in the database.

    Args:
        session: Database session
        map_id: Map UUID

    Returns:
        Number of POIs enriched
    """
    from uuid import UUID
    from api.database.repositories.map_poi import MapPOIRepository
    from api.models.road_models import MilestoneType

    settings = get_settings()

    # Check if enrichment is enabled
    if not settings.google_places_enabled:
        logger.debug("Google Places enrichment is disabled (GOOGLE_PLACES_ENABLED=false)")
        return 0
    if not settings.google_places_api_key:
        logger.warning(
            "Google Places enrichment skipped: GOOGLE_PLACES_API_KEY not configured. "
            "Add GOOGLE_PLACES_API_KEY to .env to enable restaurant/hotel ratings."
        )
        return 0

    # Map POI types to MilestoneType for checking enrichable types
    TYPE_TO_MILESTONE = {
        "restaurant": MilestoneType.RESTAURANT,
        "fast_food": MilestoneType.FAST_FOOD,
        "cafe": MilestoneType.CAFE,
        "bar": MilestoneType.BAR,
        "pub": MilestoneType.PUB,
        "bakery": MilestoneType.BAKERY,
        "hotel": MilestoneType.HOTEL,
    }

    map_poi_repo = MapPOIRepository(session)
    service = GooglePlacesService(session)

    # Get POIs for the map
    map_pois = await map_poi_repo.get_pois_for_map(UUID(map_id), include_poi_details=True)
    db_pois = [mp.poi for mp in map_pois if mp.poi]

    enriched_count = 0

    for db_poi in db_pois:
        # Check if this POI type is enrichable
        milestone_type = TYPE_TO_MILESTONE.get(db_poi.type)
        if milestone_type not in ENRICHABLE_TYPES:
            continue

        # Skip if already has rating
        if db_poi.rating is not None:
            continue

        # Get Google Places data
        try:
            place_data = await service.get_place_data(
                osm_poi_id=db_poi.osm_id or str(db_poi.id),
                name=db_poi.name,
                latitude=float(db_poi.latitude),
                longitude=float(db_poi.longitude),
                poi_type=milestone_type,
            )

            if place_data and place_data.rating is not None:
                # Update POI with Google Places data
                db_poi.rating = place_data.rating
                db_poi.rating_count = place_data.rating_count
                db_poi.google_maps_uri = place_data.google_maps_uri
                if "google_places" not in (db_poi.enriched_by or []):
                    db_poi.enriched_by = (db_poi.enriched_by or []) + ["google_places"]
                enriched_count += 1

            # Rate limiting
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.warning(f"Error enriching POI {db_poi.id} with Google Places: {e}")

    logger.info(
        f"Google Places enrichment: {enriched_count} POIs enriched "
        f"(out of {len(db_pois)} total)"
    )
    return enriched_count
