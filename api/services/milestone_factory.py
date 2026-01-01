"""
Milestone Factory - Create and manage road milestones from POIs.

This service handles:
- Creating RoadMilestone objects from POI data
- Assigning milestones to road segments
- Enriching milestones with city information
- Category and type conversions
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from api.models.road_models import (
    Coordinates,
    LinearRoadSegment,
    MilestoneType,
    RoadMilestone,
)
from api.providers.base import GeoProvider
from api.providers.models import POI, POICategory
from api.services.poi_quality_service import POIQualityService, format_opening_hours
from api.utils.geo_utils import calculate_distance_meters

logger = logging.getLogger(__name__)


# Category to milestone type mapping
POI_CATEGORY_TO_MILESTONE_TYPE = {
    POICategory.GAS_STATION: MilestoneType.GAS_STATION,
    POICategory.FUEL: MilestoneType.GAS_STATION,
    POICategory.RESTAURANT: MilestoneType.RESTAURANT,
    POICategory.FOOD: MilestoneType.RESTAURANT,
    POICategory.HOTEL: MilestoneType.HOTEL,
    POICategory.LODGING: MilestoneType.HOTEL,
    POICategory.CAMPING: MilestoneType.CAMPING,
    POICategory.HOSPITAL: MilestoneType.HOSPITAL,
    POICategory.SERVICES: MilestoneType.OTHER,
    POICategory.PARKING: MilestoneType.OTHER,
}


class MilestoneFactory:
    """
    Factory for creating and managing road milestones.

    This class provides methods to convert POIs to milestones,
    assign them to segments, and enrich them with additional data.
    """

    def __init__(
        self,
        geo_provider: Optional[GeoProvider] = None,
        quality_service: Optional[POIQualityService] = None,
    ):
        """
        Initialize the MilestoneFactory.

        Args:
            geo_provider: Provider for reverse geocoding (to get city info)
            quality_service: Service for quality assessment (optional)
        """
        self.geo_provider = geo_provider
        self.quality_service = quality_service or POIQualityService()

    def get_milestone_type(self, category: POICategory) -> MilestoneType:
        """
        Convert POI category to milestone type.

        Args:
            category: POICategory enum value

        Returns:
            Corresponding MilestoneType
        """
        return POI_CATEGORY_TO_MILESTONE_TYPE.get(category, MilestoneType.OTHER)

    def build_milestone_categories(
        self, include_cities: bool = True
    ) -> List[POICategory]:
        """
        Build list of POI categories to search for milestones.

        Always includes all POI types for comprehensive search.
        Frontend will filter which ones to display.

        Args:
            include_cities: Whether to include city/services category

        Returns:
            List of POICategory enums
        """
        categories = [
            POICategory.GAS_STATION,
            POICategory.FUEL,
            POICategory.RESTAURANT,
            POICategory.FOOD,
            POICategory.HOTEL,
            POICategory.LODGING,
            POICategory.CAMPING,
            POICategory.HOSPITAL,
        ]

        # Cities/services based on parameter
        if include_cities:
            categories.append(POICategory.SERVICES)

        return categories

    def create_from_poi(
        self,
        poi: POI,
        distance_from_origin: float,
        route_point: Tuple[float, float],
        junction_info: Optional[Tuple[float, Tuple[float, float], float, str]] = None,
    ) -> RoadMilestone:
        """
        Create a RoadMilestone from a POI object.

        Args:
            poi: POI object from provider
            distance_from_origin: Distance from route origin in km
            route_point: (lat, lon) of the route point near this POI
            junction_info: Optional tuple of (junction_distance_km, junction_coords,
                          access_route_distance_km, side) for distant POIs

        Returns:
            RoadMilestone object
        """
        # Determine milestone type - check if it's a place (city/town/village) first
        milestone_type = None
        if poi.provider_data and "osm_tags" in poi.provider_data:
            osm_tags = poi.provider_data["osm_tags"]
            place_type = osm_tags.get("place", "")
            if place_type == "city":
                milestone_type = MilestoneType.CITY
            elif place_type == "town":
                milestone_type = MilestoneType.TOWN
            elif place_type == "village":
                milestone_type = MilestoneType.VILLAGE

        # If not a place, use category mapping
        if not milestone_type:
            milestone_type = self.get_milestone_type(poi.category)

        # Calculate distance from POI to route point
        distance_from_road = calculate_distance_meters(
            poi.location.latitude,
            poi.location.longitude,
            route_point[0],
            route_point[1],
        )

        # Extract city from POI tags (quick, no API call)
        city = self._extract_city_from_poi(poi, milestone_type)

        # Extract quality_score from provider_data
        quality_score = None
        if poi.provider_data:
            quality_score = poi.provider_data.get("quality_score")

        # Process junction information for distant POIs
        requires_detour = distance_from_road > 500  # POIs > 500m require detour
        junction_distance_km = None
        junction_coordinates = None
        access_route_distance_m = distance_from_road  # Default to straight-line distance
        poi_side = "center"  # Default side

        if junction_info:
            junction_dist_km, junction_coords, access_route_distance_km, side = (
                junction_info
            )

            # If distance from junction to POI is < 0.1km, treat as roadside POI
            if access_route_distance_km < 0.1:
                requires_detour = False
                junction_distance_km = None
                junction_coordinates = None
            else:
                junction_distance_km = junction_dist_km
                junction_coordinates = Coordinates(
                    latitude=junction_coords[0], longitude=junction_coords[1]
                )
                # Use access route distance instead of straight-line distance
                access_route_distance_m = access_route_distance_km * 1000
                poi_side = side  # Use calculated side (left or right)

        return RoadMilestone(
            id=poi.id,
            name=poi.name,
            type=milestone_type,
            coordinates=Coordinates(
                latitude=poi.location.latitude,
                longitude=poi.location.longitude,
            ),
            distance_from_origin_km=distance_from_origin,
            distance_from_road_meters=access_route_distance_m,
            side=poi_side,
            tags=poi.provider_data,
            city=city,
            operator=poi.subcategory,
            brand=poi.subcategory,
            opening_hours=format_opening_hours(poi.opening_hours),
            phone=poi.phone,
            website=poi.website,
            amenities=poi.amenities,
            quality_score=quality_score,
            # Junction information
            junction_distance_km=junction_distance_km,
            junction_coordinates=junction_coordinates,
            requires_detour=requires_detour,
        )

    def _extract_city_from_poi(
        self, poi: POI, milestone_type: MilestoneType
    ) -> Optional[str]:
        """
        Extract city name from POI data without API calls.

        Args:
            poi: POI object
            milestone_type: Type of milestone

        Returns:
            City name if found, None otherwise
        """
        if not poi.provider_data:
            return None

        # For cities and towns, the city field is the place name itself
        if milestone_type in [MilestoneType.CITY, MilestoneType.TOWN]:
            return poi.name

        # For villages, city should be the municipality name
        if milestone_type == MilestoneType.VILLAGE:
            osm_tags = poi.provider_data.get("osm_tags", {})
            return (
                osm_tags.get("addr:city")
                or osm_tags.get("is_in:city")
                or osm_tags.get("is_in")
                or poi.provider_data.get("addr:city")
                or poi.provider_data.get("address:city")
                or poi.provider_data.get("addr:municipality")
            )

        # For other POIs, try to extract city from address tags
        return (
            poi.provider_data.get("addr:city")
            or poi.provider_data.get("address:city")
            or poi.provider_data.get("addr:municipality")
        )

    def assign_to_segments(
        self,
        segments: List[LinearRoadSegment],
        milestones: List[RoadMilestone],
    ) -> None:
        """
        Assign milestones to their respective segments based on distance.

        Modifies segments in-place.

        Args:
            segments: List of road segments
            milestones: List of milestones to assign
        """
        for segment in segments:
            segment.milestones = [
                milestone
                for milestone in milestones
                if segment.start_distance_km
                <= milestone.distance_from_origin_km
                <= segment.end_distance_km
            ]
            segment.milestones.sort(key=lambda m: m.distance_from_origin_km)

    async def enrich_with_cities(
        self, milestones: List[RoadMilestone]
    ) -> None:
        """
        Enrich milestones with city information via reverse geocoding.

        Only geocodes milestones that don't already have city information.
        Modifies milestones in-place.

        Args:
            milestones: List of milestones to enrich
        """
        if not self.geo_provider:
            logger.warning("No geo_provider configured for city enrichment")
            return

        milestones_without_city = [m for m in milestones if not m.city]
        logger.info(f"Reverse geocoding for city info...")
        logger.info(
            f"{len(milestones_without_city)} POIs need reverse geocoding"
        )

        for milestone in milestones_without_city:
            try:
                reverse_loc = await self.geo_provider.reverse_geocode(
                    milestone.coordinates.latitude,
                    milestone.coordinates.longitude,
                    poi_name=milestone.name,
                )
                if reverse_loc and reverse_loc.city:
                    milestone.city = reverse_loc.city
            except Exception:
                pass  # Reverse geocoding failure is not critical

        cities_found = len([m for m in milestones if m.city])
        logger.info(
            f"Reverse geocoding complete: "
            f"{cities_found}/{len(milestones)} POIs with city identified"
        )


# Module-level functions for convenience


def get_milestone_type(category: POICategory) -> MilestoneType:
    """Convert POI category to milestone type."""
    return POI_CATEGORY_TO_MILESTONE_TYPE.get(category, MilestoneType.OTHER)


def build_milestone_categories(include_cities: bool = True) -> List[POICategory]:
    """Build list of POI categories for milestone search."""
    return MilestoneFactory().build_milestone_categories(include_cities)


def assign_milestones_to_segments(
    segments: List[LinearRoadSegment], milestones: List[RoadMilestone]
) -> None:
    """Assign milestones to segments based on distance."""
    MilestoneFactory().assign_to_segments(segments, milestones)
