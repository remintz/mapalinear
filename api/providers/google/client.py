"""
Google Places API client for fetching POI ratings.

Uses the Places API (Legacy) for searching nearby places and getting ratings.
https://developers.google.com/maps/documentation/places/web-service/search-nearby
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GooglePlaceResult:
    """Result from Google Places API search."""

    place_id: str
    name: str
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    google_maps_uri: Optional[str] = None
    distance_meters: Optional[float] = None


class GooglePlacesClient:
    """
    Client for Google Places API (Legacy).

    Uses Nearby Search to find places by location and name,
    returning ratings and Google Maps URLs.
    """

    # API endpoints (Legacy)
    NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        rate_limit_delay: float = 0.1,  # 100ms between requests
    ):
        """
        Initialize the Google Places client.

        Args:
            api_key: Google Cloud API key with Places API enabled
            timeout: Request timeout in seconds
            rate_limit_delay: Minimum delay between requests (seconds)
        """
        self.api_key = api_key
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _rate_limit(self):
        """Ensure minimum delay between requests."""
        import time

        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        name: str,
        radius_meters: float = 100.0,
        max_results: int = 5,
    ) -> Optional[GooglePlaceResult]:
        """
        Search for a place near the given coordinates.

        Args:
            latitude: Latitude of the search center
            longitude: Longitude of the search center
            name: Name of the place to search for (used as keyword)
            radius_meters: Search radius in meters
            max_results: Maximum number of results to return

        Returns:
            GooglePlaceResult if found, None otherwise
        """
        await self._rate_limit()

        client = await self._get_client()

        # Build request params for Nearby Search (Legacy)
        params = {
            "location": f"{latitude},{longitude}",
            "radius": int(radius_meters),
            "keyword": name,
            "key": self.api_key,
        }

        try:
            response = await client.get(self.NEARBY_SEARCH_URL, params=params)

            if response.status_code == 200:
                data = response.json()
                status = data.get("status")

                if status == "OK" and data.get("results"):
                    places = data["results"][:max_results]

                    # Find best match by name similarity
                    best_match = self._find_best_match(places, name)

                    if best_match:
                        return self._parse_place(best_match, latitude, longitude)

                    # If no good name match, return first result
                    return self._parse_place(places[0], latitude, longitude)

                elif status == "ZERO_RESULTS":
                    logger.debug(f"No places found near ({latitude}, {longitude}) for '{name}'")
                    return None
                else:
                    logger.warning(f"Google Places API status: {status}")
                    return None

            elif response.status_code == 429:
                logger.warning("Google Places API rate limit exceeded")
                return None
            else:
                logger.error(
                    f"Google Places API error: {response.status_code} - {response.text}"
                )
                return None

        except httpx.TimeoutException:
            logger.warning(f"Google Places API timeout for ({latitude}, {longitude})")
            return None
        except Exception as e:
            logger.error(f"Google Places API error: {e}")
            return None

    def _find_best_match(self, places: list, search_name: str) -> Optional[dict]:
        """
        Find the best matching place by name similarity.

        Args:
            places: List of places from API response
            search_name: Name we're searching for

        Returns:
            Best matching place or None
        """
        if not search_name or not places:
            return None

        search_name_lower = search_name.lower().strip()

        # First pass: exact match
        for place in places:
            place_name = place.get("name", "").lower()
            if place_name == search_name_lower:
                return place

        # Second pass: contains match
        for place in places:
            place_name = place.get("name", "").lower()
            if search_name_lower in place_name or place_name in search_name_lower:
                return place

        # Third pass: word overlap
        search_words = set(search_name_lower.split())
        best_score = 0
        best_place = None

        for place in places:
            place_name = place.get("name", "").lower()
            place_words = set(place_name.split())
            overlap = len(search_words & place_words)

            if overlap > best_score:
                best_score = overlap
                best_place = place

        return best_place if best_score > 0 else None

    def _parse_place(
        self, place: dict, search_lat: float, search_lng: float
    ) -> GooglePlaceResult:
        """Parse a place from the Legacy API response."""
        place_id = place.get("place_id", "")
        name = place.get("name", "Unknown")

        # Calculate distance if geometry is available
        distance = None
        geometry = place.get("geometry", {})
        location = geometry.get("location", {})
        if location:
            place_lat = location.get("lat")
            place_lng = location.get("lng")
            if place_lat and place_lng:
                distance = self._haversine_distance(
                    search_lat, search_lng, place_lat, place_lng
                )

        # Build Google Maps URL from place_id
        google_maps_uri = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        return GooglePlaceResult(
            place_id=place_id,
            name=name,
            rating=place.get("rating"),
            user_rating_count=place.get("user_ratings_total"),
            google_maps_uri=google_maps_uri,
            distance_meters=distance,
        )

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters."""
        from math import radians, cos, sin, asin, sqrt

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371000  # Earth radius in meters

        return c * r

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
