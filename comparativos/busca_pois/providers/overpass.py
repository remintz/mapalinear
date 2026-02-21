"""
Overpass API provider for POI search.
"""

import asyncio
import json
import time
from typing import List
import httpx

from .base import POIProvider, POIResult
from constants import OVERPASS_ENDPOINTS, OVERPASS_CATEGORY_MAP


class OverpassProvider(POIProvider):
    """Provider using Overpass API (OpenStreetMap)."""
    
    def __init__(self):
        super().__init__("Overpass")
        self.endpoints = OVERPASS_ENDPOINTS
        self.current_endpoint = 0
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _build_query(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        categories: List[str]
    ) -> str:
        """Build Overpass QL query."""
        # Collect all tags to search for
        tags = []
        for cat in categories:
            if cat in OVERPASS_CATEGORY_MAP:
                tags.extend(OVERPASS_CATEGORY_MAP[cat])
        
        # Remove duplicates
        tags = list(set(tags))
        
        if not tags:
            tags = ["amenity=fuel", "amenity=restaurant"]
        
        # Convert radius to degrees (approximate)
        radius_deg = radius / 111000
        
        # Calculate bounding box
        south = latitude - radius_deg
        west = longitude - radius_deg
        north = latitude + radius_deg
        east = longitude + radius_deg
        bbox = f"{south},{west},{north},{east}"
        
        # Build query using bbox (same as MapaLinear)
        query_parts = ['[out:json][timeout:25];', '(']
        
        for tag in tags:
            key, value = tag.split('=')
            query_parts.append(f'  node["{key}"="{value}"]({bbox});')
            query_parts.append(f'  way["{key}"="{value}"]({bbox});')
        
        query_parts.extend([');', 'out center tags;'])
        
        return '\n'.join(query_parts)
    
    async def search_pois(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        categories: List[str],
    ) -> List[POIResult]:
        """Search POIs using Overpass API."""
        query = self._build_query(latitude, longitude, radius, categories)
        
        endpoint = self.endpoints[self.current_endpoint]
        self.current_endpoint = (self.current_endpoint + 1) % len(self.endpoints)
        
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        
        start_time = time.time()
        self.total_requests += 1
        
        try:
            response = await self.client.post(
                endpoint,
                data={"data": query}
            )
            response.raise_for_status()
            data = response.json()
            
            self.total_time += time.time() - start_time
            self.last_request_time = time.time()
            
            return self._parse_results(data, categories)
            
        except Exception as e:
            self.total_time += time.time() - start_time
            self.last_request_time = time.time()
            print(f"  [Overpass] Erro: {e}")
            return []
    
    def _parse_results(self, data: dict, categories: List[str]) -> List[POIResult]:
        """Parse Overpass response into POI results."""
        results = []
        
        for element in data.get("elements", []):
            try:
                tags = element.get("tags", {})
                name = tags.get("name", tags.get("brand", "Sem nome"))
                
                # Determine category from tags
                category = self._determine_category(tags, categories)
                
                # Get coordinates
                if element["type"] == "node":
                    lat = element.get("lat", 0)
                    lon = element.get("lon", 0)
                elif element.get("center"):
                    lat = element["center"].get("lat", 0)
                    lon = element["center"].get("lon", 0)
                else:
                    continue
                
                # Build POI result
                poi = POIResult(
                    id=f"osm_{element['type']}_{element['id']}",
                    name=name,
                    category=category,
                    latitude=lat,
                    longitude=lon,
                    address=tags.get("addr:street"),
                    phone=tags.get("phone"),
                    website=tags.get("website"),
                    raw_data=tags
                )
                results.append(poi)
                
            except Exception as e:
                print(f"    [Overpass] Parse error: {e}")
                continue
        
        return results
    
    def _determine_category(self, tags: dict, categories: List[str]) -> str:
        """Determine POI category from OSM tags."""
        # Check for fuel
        if tags.get("amenity") == "fuel":
            return "gas_station"
        
        # Check for restaurant/food
        if tags.get("amenity") in ("restaurant", "fast_food", "food_court"):
            return "restaurant"
        
        # Check for hotel/lodging
        if tags.get("tourism") in ("hotel", "motel", "guest_house"):
            return "hotel"
        
        # Check for camping
        if tags.get("tourism") == "camping":
            return "camping"
        
        # Check for hospital
        if tags.get("amenity") in ("hospital", "clinic"):
            return "hospital"
        
        # Check for place
        if tags.get("place") in ("city", "town", "village"):
            return tags.get("place")
        
        return "other"
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
