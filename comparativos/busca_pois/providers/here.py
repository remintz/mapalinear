"""
HERE Maps provider for POI search.
"""

import asyncio
import time
from typing import List
import httpx

from .base import POIProvider, POIResult
from constants import HERE_API_KEY, HERE_CATEGORY_MAP


class HereProvider(POIProvider):
    """Provider using HERE Maps Browse API."""
    
    def __init__(self, api_key: str = None):
        super().__init__("HERE")
        self.api_key = api_key or HERE_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if not self.api_key:
            raise ValueError("HERE_API_KEY não configurado")
    
    async def search_pois(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        categories: List[str],
    ) -> List[POIResult]:
        """Search POIs using HERE Browse API."""
        # Collect unique HERE categories
        here_categories = set()
        for cat in categories:
            if cat in HERE_CATEGORY_MAP and HERE_CATEGORY_MAP[cat]:
                here_categories.add(HERE_CATEGORY_MAP[cat])
        
        if not here_categories:
            return []
        
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.3:
            await asyncio.sleep(0.3 - elapsed)
        
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Use HERE Browse API
            url = "https://browse.search.hereapi.com/v1/browse"
            
            params = {
                "at": f"{latitude},{longitude}",
                "categories": ",".join(here_categories),
                "limit": 50,
                "apiKey": self.api_key,
                "lang": "pt-BR",
                "in": f"circle:{latitude},{longitude};r={radius}"
            }
            
            response = await self.client.get(url, params=params)
            
            self.total_time += time.time() - start_time
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data, categories)
            else:
                print(f"  [HERE] Erro HTTP {response.status_code}")
                
        except Exception as e:
            self.total_time += time.time() - start_time
            self.last_request_time = time.time()
            print(f"  [HERE] Erro: {e}")
        
        return []
    
    def _parse_results(self, data: dict, categories: List[str]) -> List[POIResult]:
        """Parse HERE response into POI results."""
        results = []
        
        for item in data.get("items", []):
            try:
                # Get position
                pos = item.get("position", {})
                lat = pos.get("lat", 0)
                lon = pos.get("lng", 0)
                
                # Get title (name)
                name = item.get("title", "Sem nome")
                
                # Get category
                categories_data = item.get("categories", [])
                category = self._determine_category(categories_data)
                
                # Get address
                address = item.get("address", {})
                address_str = address.get("label", "")
                
                # Get contact info
                contact = item.get("contact", {})
                phone = contact.get("phone", [{}])[0].get("value") if contact.get("phone") else None
                website = contact.get("www", [{}])[0].get("value") if contact.get("www") else None
                
                # Get rating
                rating = item.get("rating", {}).get("average")
                
                poi = POIResult(
                    id=f"here_{item.get('id', '')}",
                    name=name,
                    category=category,
                    latitude=lat,
                    longitude=lon,
                    address=address_str,
                    phone=phone,
                    website=website,
                    rating=rating,
                    raw_data=item
                )
                results.append(poi)
                
            except Exception as e:
                continue
        
        return results
    
    def _determine_category(self, categories_data: List[dict]) -> str:
        """Determine POI category from HERE categories."""
        if not categories_data:
            return "other"
        
        # Get first category
        first_cat = categories_data[0].get("name", "").lower()
        
        # Also check all categories
        all_cats = " ".join([c.get("name", "").lower() for c in categories_data])
        
        if "fuel" in all_cats or "petrol" in all_cats:
            return "gas_station"
        if "restaurant" in all_cats or "food" in all_cats or "cafe" in all_cats:
            return "restaurant"
        if "hotel" in all_cats or "motel" in all_cats:
            return "hotel"
        if "camp" in all_cats:
            return "camping"
        if "hospital" in all_cats or "clinic" in all_cats or "medical" in all_cats:
            return "hospital"
        
        return "other"
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()