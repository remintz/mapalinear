"""
POI Search Service - Core service for finding POIs along routes.

This service handles searching for POIs around route segments.
Side determination and junction calculation are handled by JunctionCalculationService.
"""

import logging
from typing import Dict, List, Optional, Tuple

from api.database.models.route_segment import RouteSegment
from api.providers.base import GeoProvider
from api.providers.models import GeoLocation, POI, POICategory
from api.services.milestone_factory import MilestoneFactory
from api.services.poi_quality_service import POIQualityService
from api.utils.geo_utils import calculate_distance_meters

logger = logging.getLogger(__name__)


class POISearchService:
    """
    Service for searching POIs along a route.

    This service finds POIs near route segments. Junction calculation
    and side determination are handled by JunctionCalculationService.
    """

    def __init__(
        self,
        geo_provider: GeoProvider,
        poi_provider: GeoProvider,
        milestone_factory: Optional[MilestoneFactory] = None,
        quality_service: Optional[POIQualityService] = None,
    ):
        """
        Initialize the POI Search Service.

        Args:
            geo_provider: Provider for routing/geocoding
            poi_provider: Provider for POI search
            milestone_factory: Factory for creating milestones (optional)
            quality_service: Service for quality assessment (optional)
        """
        self.geo_provider = geo_provider
        self.poi_provider = poi_provider
        self.milestone_factory = milestone_factory or MilestoneFactory(geo_provider)
        self.quality_service = quality_service or POIQualityService()

    async def search_pois_for_segment(
        self,
        segment: RouteSegment,
        categories: List[POICategory],
        max_distance_from_road: float = 3000,
    ) -> List[Tuple[POI, int, int]]:
        """
        Search for POIs using a segment's pre-computed search points.

        This method is optimized for the reusable segments architecture:
        - Uses the segment's stored search_points
        - Returns POIs with discovery metadata for SegmentPOI creation

        Args:
            segment: RouteSegment with pre-computed search_points
            categories: POI categories to search for
            max_distance_from_road: Maximum search radius in meters

        Returns:
            List of tuples (POI, search_point_index, straight_line_distance_m)
        """
        if not segment.search_points:
            logger.debug(f"Segment {segment.id} has no search points")
            return []

        # Track unique POIs with best discovery data
        # Key: poi_id, Value: (POI, search_point_index, distance_m)
        best_discovery: Dict[str, Tuple[POI, int, int]] = {}

        for sp in segment.search_points:
            sp_index = sp["index"]
            sp_lat = sp["lat"]
            sp_lon = sp["lon"]

            try:
                pois = await self.poi_provider.search_pois(
                    location=GeoLocation(latitude=sp_lat, longitude=sp_lon),
                    radius=max_distance_from_road,
                    categories=categories,
                    limit=20,
                )

                for poi in pois:
                    # Calculate straight-line distance
                    distance_m = int(
                        calculate_distance_meters(
                            poi.location.latitude,
                            poi.location.longitude,
                            sp_lat,
                            sp_lon,
                        )
                    )

                    # Skip abandoned POIs
                    provider_data = poi.provider_data or {}
                    if provider_data.get("is_abandoned", False):
                        continue

                    # Keep best (closest) discovery for each POI
                    if poi.id in best_discovery:
                        _, _, prev_distance = best_discovery[poi.id]
                        if distance_m < prev_distance:
                            best_discovery[poi.id] = (poi, sp_index, distance_m)
                    else:
                        best_discovery[poi.id] = (poi, sp_index, distance_m)

            except Exception as e:
                logger.warning(
                    f"Error searching POIs at search point {sp_index}: {e}"
                )
                continue

        logger.info(
            f"Found {len(best_discovery)} unique POIs for segment {segment.id}"
        )

        return list(best_discovery.values())
