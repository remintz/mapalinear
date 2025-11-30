"""
Google Places POI Provider.

Provides POI search functionality using Google Places API,
returning POIs with ratings and reviews included.
"""

import asyncio
import logging
import os
from typing import List, Optional

import httpx

from api.providers.models import GeoLocation, POI, POICategory

logger = logging.getLogger(__name__)


# Mapping from our POICategory to Google Places types
CATEGORY_TO_GOOGLE_TYPES = {
    POICategory.GAS_STATION: ["gas_station"],
    POICategory.FUEL: ["gas_station"],
    POICategory.RESTAURANT: ["restaurant", "meal_takeaway"],
    POICategory.FOOD: ["restaurant", "cafe", "bakery", "meal_takeaway"],
    POICategory.HOTEL: ["lodging", "hotel"],
    POICategory.LODGING: ["lodging", "hotel", "motel"],
    POICategory.CAMPING: ["campground", "rv_park"],
    POICategory.HOSPITAL: ["hospital"],
    POICategory.PHARMACY: ["pharmacy"],
    POICategory.BANK: ["bank"],
    POICategory.ATM: ["atm"],
    POICategory.SHOPPING: ["shopping_mall", "store"],
    POICategory.TOURIST_ATTRACTION: ["tourist_attraction"],
    POICategory.REST_AREA: ["rest_stop"],
    POICategory.PARKING: ["parking"],
    POICategory.SERVICES: ["car_repair", "car_wash"],
}

# Reverse mapping for parsing results
GOOGLE_TYPE_TO_CATEGORY = {
    "gas_station": POICategory.GAS_STATION,
    "restaurant": POICategory.RESTAURANT,
    "cafe": POICategory.FOOD,
    "bakery": POICategory.FOOD,
    "meal_takeaway": POICategory.FOOD,
    "lodging": POICategory.HOTEL,
    "hotel": POICategory.HOTEL,
    "motel": POICategory.LODGING,
    "campground": POICategory.CAMPING,
    "rv_park": POICategory.CAMPING,
    "hospital": POICategory.HOSPITAL,
    "pharmacy": POICategory.PHARMACY,
    "bank": POICategory.BANK,
    "atm": POICategory.ATM,
    "shopping_mall": POICategory.SHOPPING,
    "store": POICategory.SHOPPING,
    "tourist_attraction": POICategory.TOURIST_ATTRACTION,
    "rest_stop": POICategory.REST_AREA,
    "parking": POICategory.PARKING,
    "car_repair": POICategory.SERVICES,
    "car_wash": POICategory.SERVICES,
}


class GooglePlacesPOIProvider:
    """
    POI Provider using Google Places API.

    Returns POIs with ratings and reviews included.
    """

    NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 0.1,
        timeout: float = 30.0,
    ):
        """
        Initialize the Google Places POI Provider.

        Args:
            api_key: Google Places API key (falls back to env var)
            rate_limit_delay: Delay between API calls (seconds)
            timeout: Request timeout (seconds)
        """
        self.api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0

    @property
    def is_configured(self) -> bool:
        """Check if the provider has a valid API key."""
        return bool(self.api_key)

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

    async def search_pois(
        self,
        location: GeoLocation,
        radius: float,
        categories: List[POICategory],
        limit: int = 50,
    ) -> List[POI]:
        """
        Search for POIs around a location using Google Places API.

        Args:
            location: Center point for the search
            radius: Search radius in meters
            categories: List of POI categories to search for
            limit: Maximum number of results to return

        Returns:
            List of POI objects with ratings included
        """
        if not self.is_configured:
            logger.warning("Google Places API key not configured")
            return []

        # Convert categories to Google types
        google_types = set()
        for category in categories:
            if category in CATEGORY_TO_GOOGLE_TYPES:
                google_types.update(CATEGORY_TO_GOOGLE_TYPES[category])

        if not google_types:
            logger.warning(f"No Google types for categories: {categories}")
            return []

        all_pois = []
        seen_place_ids = set()

        # Search for each type separately (Google API limitation)
        for google_type in google_types:
            if len(all_pois) >= limit:
                break

            pois = await self._search_by_type(
                location=location,
                radius=radius,
                place_type=google_type,
                limit=limit - len(all_pois),
            )

            # Deduplicate by place_id
            for poi in pois:
                if poi.id not in seen_place_ids:
                    seen_place_ids.add(poi.id)
                    all_pois.append(poi)

        logger.debug(
            f"Google Places found {len(all_pois)} POIs near "
            f"({location.latitude}, {location.longitude})"
        )

        return all_pois[:limit]

    async def _search_by_type(
        self,
        location: GeoLocation,
        radius: float,
        place_type: str,
        limit: int,
    ) -> List[POI]:
        """Search for POIs of a specific Google type."""
        await self._rate_limit()

        client = await self._get_client()

        params = {
            "location": f"{location.latitude},{location.longitude}",
            "radius": int(min(radius, 50000)),  # Google max is 50km
            "type": place_type,
            "key": self.api_key,
        }

        try:
            response = await client.get(self.NEARBY_SEARCH_URL, params=params)

            if response.status_code != 200:
                logger.error(f"Google Places API error: {response.status_code}")
                return []

            data = response.json()
            status = data.get("status")

            if status == "OK":
                return [
                    self._parse_place(place)
                    for place in data.get("results", [])[:limit]
                ]
            elif status == "ZERO_RESULTS":
                return []
            else:
                logger.warning(f"Google Places API status: {status}")
                return []

        except httpx.TimeoutException:
            logger.warning("Google Places API timeout")
            return []
        except Exception as e:
            logger.error(f"Google Places API error: {e}")
            return []

    def _parse_place(self, place: dict) -> POI:
        """Parse a Google Place into our POI model."""
        place_id = place.get("place_id", "")
        name = place.get("name", "Unknown")

        # Extract location
        geometry = place.get("geometry", {})
        loc = geometry.get("location", {})
        latitude = loc.get("lat", 0)
        longitude = loc.get("lng", 0)

        # Determine category from Google types
        types = place.get("types", [])
        category = POICategory.SERVICES  # Default
        for t in types:
            if t in GOOGLE_TYPE_TO_CATEGORY:
                category = GOOGLE_TYPE_TO_CATEGORY[t]
                break

        # Extract rating info
        rating = place.get("rating")
        review_count = place.get("user_ratings_total")

        # Build Google Maps URL
        google_maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        # Extract other info
        opening_hours = place.get("opening_hours", {})
        is_open = opening_hours.get("open_now") if opening_hours else None

        return POI(
            id=f"google/{place_id}",
            name=name,
            location=GeoLocation(
                latitude=latitude,
                longitude=longitude,
                address=place.get("vicinity"),
            ),
            category=category,
            subcategory=types[0] if types else None,
            rating=rating,
            review_count=review_count,
            is_open=is_open,
            provider_data={
                "google_place_id": place_id,
                "google_maps_url": google_maps_url,
                "google_types": types,
                "price_level": place.get("price_level"),
                "business_status": place.get("business_status"),
            },
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Singleton instance
_provider_instance: Optional[GooglePlacesPOIProvider] = None


def get_google_poi_provider() -> GooglePlacesPOIProvider:
    """Get or create the Google Places POI provider singleton."""
    global _provider_instance

    if _provider_instance is None:
        _provider_instance = GooglePlacesPOIProvider()

    return _provider_instance
