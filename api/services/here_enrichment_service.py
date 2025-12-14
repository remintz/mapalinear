"""
HERE Maps Enrichment Service.

Enriches existing POIs (typically from OSM) with additional data from HERE Maps,
including phone numbers, websites, opening hours, and structured addresses.
"""
import asyncio
import logging
import math
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.providers.settings import get_settings
from api.database.models.poi import POI as DBPoi
from api.database.repositories.poi import POIRepository
from api.providers.here.provider import HEREProvider
from api.providers.models import GeoLocation, POI, POICategory

logger = logging.getLogger(__name__)


@dataclass
class HereEnrichmentResult:
    """Result of HERE enrichment for a single POI."""

    poi_id: str
    osm_id: Optional[str]
    here_id: Optional[str]
    matched: bool
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None
    match_distance_meters: Optional[float] = None
    error: Optional[str] = None


# POI types that can be enriched with HERE data
ENRICHABLE_TYPES = [
    "gas_station",
    "restaurant",
    "hotel",
    "hospital",
    "pharmacy",
    "bank",
    "atm",
    "cafe",
    "fast_food",
    "supermarket",
    "mechanic",
]


# Map of database POI types to POICategory enum
TYPE_TO_CATEGORY = {
    "gas_station": POICategory.GAS_STATION,
    "restaurant": POICategory.RESTAURANT,
    "hotel": POICategory.HOTEL,
    "hospital": POICategory.HOSPITAL,
    "pharmacy": POICategory.PHARMACY,
    "bank": POICategory.BANK,
    "atm": POICategory.ATM,
    "cafe": POICategory.CAFE,
    "fast_food": POICategory.FAST_FOOD,
    "supermarket": POICategory.SUPERMARKET,
    "mechanic": POICategory.MECHANIC,
    "police": POICategory.POLICE,
}


class HereEnrichmentService:
    """Service for enriching POIs with HERE Maps data."""

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize the service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.settings = get_settings()
        self.session = session
        self.poi_repo = POIRepository(session) if session else None
        self._here_provider: Optional[HEREProvider] = None

    @property
    def here_provider(self) -> HEREProvider:
        """Lazy initialization of HERE provider."""
        if self._here_provider is None:
            self._here_provider = HEREProvider()
        return self._here_provider

    def is_enabled(self) -> bool:
        """Check if HERE enrichment is enabled and configured."""
        return self.settings.here_api_key is not None

    def should_enrich(self, poi: DBPoi) -> bool:
        """Check if a POI should be enriched with HERE data."""
        return (
            poi.type in ENRICHABLE_TYPES
            and not poi.is_enriched_by("here_maps")
        )

    async def enrich_poi(
        self,
        poi: DBPoi,
        search_radius: float = 100.0,
    ) -> HereEnrichmentResult:
        """
        Enrich a single POI with HERE Maps data.

        Args:
            poi: Database POI to enrich
            search_radius: Search radius in meters (default 100m)

        Returns:
            HereEnrichmentResult with enrichment details
        """
        if not self.is_enabled():
            return HereEnrichmentResult(
                poi_id=str(poi.id),
                osm_id=poi.osm_id,
                here_id=None,
                matched=False,
                error="HERE Maps enrichment is disabled"
            )

        if poi.is_enriched_by("here_maps"):
            return HereEnrichmentResult(
                poi_id=str(poi.id),
                osm_id=poi.osm_id,
                here_id=poi.here_id,
                matched=True,
                error="Already enriched by HERE"
            )

        try:
            # Create location from POI coordinates
            location = GeoLocation(
                latitude=poi.latitude,
                longitude=poi.longitude
            )

            # Map POI type to category
            category = TYPE_TO_CATEGORY.get(poi.type, POICategory.OTHER)

            # Search for matching HERE POIs
            here_pois = await self.here_provider.search_pois(
                location=location,
                radius=search_radius,  # Radius in meters
                categories=[category],
                limit=5
            )

            if not here_pois:
                return HereEnrichmentResult(
                    poi_id=str(poi.id),
                    osm_id=poi.osm_id,
                    here_id=None,
                    matched=False,
                    error=f"No HERE results found within {search_radius}m"
                )

            # Find the best match
            best_match = self._find_best_match(poi, here_pois, location)

            if not best_match:
                return HereEnrichmentResult(
                    poi_id=str(poi.id),
                    osm_id=poi.osm_id,
                    here_id=None,
                    matched=False,
                    error="No suitable match found"
                )

            # Extract HERE data
            here_poi, distance = best_match
            here_id = here_poi.provider_data.get("here_id")

            # Build here_data structure
            here_data = {
                "address": here_poi.provider_data.get("address_structured", {}),
                "references": here_poi.provider_data.get("references", {}),
                "categories": here_poi.provider_data.get("here_categories", []),
                "match_distance_meters": distance,
            }

            # Extract opening hours as string
            opening_hours_str = None
            if here_poi.opening_hours:
                general_hours = here_poi.opening_hours.get("general")
                if general_hours:
                    if isinstance(general_hours, list):
                        opening_hours_str = "; ".join(general_hours)
                    else:
                        opening_hours_str = str(general_hours)

            # Update POI in database
            if self.poi_repo:
                await self.poi_repo.update_with_here_data(
                    poi=poi,
                    here_id=here_id,
                    here_data=here_data,
                    phone=here_poi.phone,
                    website=here_poi.website,
                    opening_hours=opening_hours_str,
                )
                logger.info(f"Enriched POI {poi.name} with HERE data (here_id={here_id})")

            return HereEnrichmentResult(
                poi_id=str(poi.id),
                osm_id=poi.osm_id,
                here_id=here_id,
                matched=True,
                phone=here_poi.phone,
                website=here_poi.website,
                opening_hours=opening_hours_str,
                match_distance_meters=distance
            )

        except Exception as e:
            logger.error(f"Error enriching POI {poi.name}: {e}")
            return HereEnrichmentResult(
                poi_id=str(poi.id),
                osm_id=poi.osm_id,
                here_id=None,
                matched=False,
                error=str(e)
            )

    def _find_best_match(
        self,
        db_poi: DBPoi,
        here_pois: List[POI],
        search_location: GeoLocation
    ) -> Optional[tuple[POI, float]]:
        """
        Find the best matching HERE POI for a database POI.

        Uses name similarity and distance to find the best match.

        Args:
            db_poi: Database POI to match
            here_pois: List of HERE POIs to search
            search_location: Original search location

        Returns:
            Tuple of (best matching POI, distance in meters) or None
        """
        if not here_pois:
            return None

        db_name_lower = db_poi.name.lower().strip()
        best_score = -1
        best_match = None
        best_distance = 0

        for here_poi in here_pois:
            here_name_lower = here_poi.name.lower().strip()

            # Calculate distance
            distance = self._calculate_distance(
                db_poi.latitude, db_poi.longitude,
                here_poi.location.latitude, here_poi.location.longitude
            )

            # Calculate name similarity
            name_score = 0

            # Check for exact or substring match
            if db_name_lower in here_name_lower or here_name_lower in db_name_lower:
                name_score = 1.0
            else:
                # Check for partial word matches
                db_words = set(db_name_lower.split())
                here_words = set(here_name_lower.split())
                common_words = db_words & here_words

                # Remove common generic words
                common_words -= {"posto", "fuel", "gas", "station", "restaurant",
                                "restaurante", "hotel", "pousada", "bar", "cafe"}

                if common_words:
                    name_score = len(common_words) / max(len(db_words), len(here_words))

            # Distance score (closer is better, normalized to 100m)
            distance_score = max(0, 1 - distance / 200)

            # Combined score (distance is more important for nearby matches)
            score = name_score * 0.4 + distance_score * 0.6

            if score > best_score:
                best_score = score
                best_match = here_poi
                best_distance = distance

        # Return match if score is reasonable (at least close proximity)
        if best_score > 0.3:
            return (best_match, best_distance)

        # If no good match by name, return the closest one if it's very close
        if here_pois and best_distance < 50:  # 50 meters
            return (here_pois[0], best_distance)

        return None

    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters (Haversine formula)."""
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

    async def enrich_pois(
        self,
        pois: List[DBPoi],
        search_radius: float = 100.0,
        delay_between_requests: float = 0.2,
    ) -> List[HereEnrichmentResult]:
        """
        Enrich a list of POIs with HERE Maps data.

        Args:
            pois: List of database POIs to enrich
            search_radius: Search radius in meters (default 100m)
            delay_between_requests: Delay between API calls in seconds

        Returns:
            List of enrichment results
        """
        if not self.is_enabled():
            logger.warning("HERE Maps enrichment is disabled")
            return []

        results = []
        enrichable_count = 0

        for poi in pois:
            if self.should_enrich(poi):
                enrichable_count += 1
                result = await self.enrich_poi(poi, search_radius)
                results.append(result)

                # Rate limiting
                await asyncio.sleep(delay_between_requests)

        logger.info(
            f"HERE enrichment completed: {len([r for r in results if r.matched])} matched "
            f"out of {enrichable_count} enrichable POIs"
        )
        return results

    async def enrich_unenriched_pois(
        self,
        poi_types: Optional[List[str]] = None,
        limit: int = 100,
        search_radius: float = 100.0,
    ) -> List[HereEnrichmentResult]:
        """
        Find and enrich POIs that haven't been enriched by HERE yet.

        Args:
            poi_types: Optional list of POI types to enrich
            limit: Maximum number of POIs to process
            search_radius: Search radius in meters

        Returns:
            List of enrichment results
        """
        if not self.poi_repo:
            raise ValueError("Database session required for this operation")

        # Find unenriched POIs
        pois = await self.poi_repo.find_not_enriched_by_here(
            poi_types=poi_types,
            limit=limit
        )

        logger.info(f"Found {len(pois)} POIs not yet enriched by HERE")

        return await self.enrich_pois(pois, search_radius)


async def enrich_map_pois_with_here(
    session: AsyncSession,
    map_id: str,
    poi_types: Optional[List[str]] = None,
) -> List[HereEnrichmentResult]:
    """
    Enrich all POIs in a map with HERE Maps data.

    This is a convenience function that can be called from routers.

    Args:
        session: Database session
        map_id: Map UUID
        poi_types: Optional list of POI types to enrich

    Returns:
        List of enrichment results
    """
    from api.database.repositories.map_poi import MapPOIRepository

    map_poi_repo = MapPOIRepository(session)
    service = HereEnrichmentService(session)

    if not service.is_enabled():
        return []

    # Get POIs for the map
    from uuid import UUID
    map_pois = await map_poi_repo.get_pois_for_map(UUID(map_id), include_poi_details=True)
    db_pois = [mp.poi for mp in map_pois if mp.poi]

    # Filter by types if specified
    if poi_types:
        db_pois = [p for p in db_pois if p.type in poi_types]

    # Filter to enrichable POIs
    enrichable_pois = [p for p in db_pois if service.should_enrich(p)]

    logger.info(f"Enriching {len(enrichable_pois)} POIs from map {map_id}")

    return await service.enrich_pois(enrichable_pois)
