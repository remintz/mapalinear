"""
Mapbox provider for POI search.

Uses Mapbox Search Box API (/category endpoint).
The Geocoding v5 API does NOT include POIs - only Search Box API does.

Docs: https://docs.mapbox.com/api/search/search-box/
"""

import asyncio
import math
import time
from typing import List, Optional
import httpx

from .base import POIProvider, POIResult
from constants import MAPBOX_TOKEN

# Mapbox category canonical names
# Full list: https://api.mapbox.com/search/searchbox/v1/list/category?access_token=TOKEN
MAPBOX_CATEGORY_MAP = {
    "gas_station": ["fuel_station"],
    "fuel":        ["fuel_station"],
    "restaurant":  ["restaurant"],
    "food":        ["restaurant", "fast_food"],
    "hotel":       ["hotel"],
    "lodging":     ["hotel", "motel"],
    "camping":     ["campground"],
    "hospital":    ["hospital"],
    # city/town/village não têm categoria no Search Box
}

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class MapboxProvider(POIProvider):
    """Provider using Mapbox Search Box API (/category endpoint)."""

    BASE_URL = "https://api.mapbox.com/search/searchbox/v1/category/{category}"

    def __init__(self, token: Optional[str] = None):
        super().__init__("Mapbox")
        self.token = token or MAPBOX_TOKEN
        if not self.token:
            raise ValueError("MAPBOX_ACCESS_TOKEN não configurado")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_pois(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        categories: List[str],
    ) -> List[POIResult]:
        """Search POIs using Mapbox Search Box /category endpoint."""
        results = []

        # Collect unique Mapbox canonical categories, tracking which app-category they map to
        category_pairs = []  # (mapbox_category, app_category)
        seen = set()
        for cat in categories:
            for mapbox_cat in MAPBOX_CATEGORY_MAP.get(cat, []):
                if mapbox_cat not in seen:
                    seen.add(mapbox_cat)
                    category_pairs.append((mapbox_cat, cat))

        for mapbox_cat, app_cat in category_pairs:
            # Rate limiting
            elapsed = time.time() - self.last_request_time
            if elapsed < 0.3:
                await asyncio.sleep(0.3 - elapsed)

            start_time = time.time()
            self.total_requests += 1

            try:
                url = self.BASE_URL.format(category=mapbox_cat)
                params = {
                    "access_token": self.token,
                    "proximity": f"{longitude},{latitude}",
                    "limit": 10,
                    "country": "BR",
                    "language": "pt",
                }

                response = await self.client.get(url, params=params)
                self.total_time += time.time() - start_time
                self.last_request_time = time.time()

                if response.status_code == 200:
                    data = response.json()
                    pois = self._parse_features(data, app_cat, latitude, longitude, radius)
                    results.extend(pois)
                else:
                    print(f"  [Mapbox] {mapbox_cat}: HTTP {response.status_code} - {response.text[:200]}")

            except Exception as e:
                self.total_time += time.time() - start_time
                self.last_request_time = time.time()
                print(f"  [Mapbox] Erro em {mapbox_cat}: {e}")

        return results

    def _parse_features(
        self,
        data: dict,
        category: str,
        center_lat: float,
        center_lon: float,
        max_radius_m: int,
    ) -> List[POIResult]:
        """Parse Search Box /category response and filter by radius."""
        results = []

        for feature in data.get("features", []):
            try:
                coords = feature.get("geometry", {}).get("coordinates", [])
                if len(coords) < 2:
                    continue

                poi_lon, poi_lat = coords[0], coords[1]

                # Filter by radius
                dist = _haversine_m(center_lat, center_lon, poi_lat, poi_lon)
                if dist > max_radius_m:
                    continue

                props = feature.get("properties", {})
                name = props.get("name") or "Sem nome"

                context = props.get("context", {})
                address_parts = [
                    props.get("address"),
                    context.get("place", {}).get("name"),
                    context.get("region", {}).get("name"),
                ]
                address = ", ".join(p for p in address_parts if p) or None

                phone_list = props.get("metadata", {}).get("phone", [])
                phone = phone_list[0] if phone_list else None

                website = props.get("metadata", {}).get("website")

                poi = POIResult(
                    id=f"mapbox_{feature.get('id', '')}",
                    name=name,
                    category=category,
                    latitude=poi_lat,
                    longitude=poi_lon,
                    address=address,
                    phone=phone,
                    website=website,
                    rating=None,
                    raw_data=props,
                )
                results.append(poi)

            except Exception as e:
                continue

        return results

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
