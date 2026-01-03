"""
Route Segmentation Service - Convert routes into linear road segments.

This service handles:
- Processing route geometry into linear segments
- Extracting search points from segments for POI discovery
- Coordinate interpolation along routes
"""

import logging
from typing import List, Tuple

from api.models.road_models import Coordinates, LinearRoadSegment
from api.providers.models import Route
from api.utils.geo_utils import interpolate_coordinate_at_distance

logger = logging.getLogger(__name__)


class RouteSegmentationService:
    """
    Service for segmenting routes into linear road segments.

    This service takes a Route object and converts it into a list of
    LinearRoadSegment objects suitable for displaying in a linear map.
    """

    def process_route_into_segments(
        self, route: Route, segment_length_km: float = 1.0
    ) -> List[LinearRoadSegment]:
        """
        Process a unified Route object into linear road segments.

        Args:
            route: Route object with geometry and metadata
            segment_length_km: Target length for each segment in km

        Returns:
            List of LinearRoadSegment objects
        """
        linear_segments = []
        total_distance = route.total_distance

        # Create segments based on the specified segment length
        current_distance = 0.0
        segment_id = 1

        while current_distance < total_distance:
            start_distance = current_distance
            end_distance = min(current_distance + segment_length_km, total_distance)

            # Calculate start and end coordinates by interpolating along the route geometry
            start_coord = interpolate_coordinate_at_distance(
                route.geometry, start_distance, total_distance
            )
            end_coord = interpolate_coordinate_at_distance(
                route.geometry, end_distance, total_distance
            )

            # Get primary road name from route
            road_name = (
                route.road_names[0] if route.road_names else "Unnamed Road"
            )

            segment = LinearRoadSegment(
                id=f"segment_{segment_id}",
                name=road_name,
                start_distance_km=start_distance,
                end_distance_km=end_distance,
                length_km=end_distance - start_distance,
                start_coordinates=Coordinates(
                    latitude=start_coord[0], longitude=start_coord[1]
                ),
                end_coordinates=Coordinates(
                    latitude=end_coord[0], longitude=end_coord[1]
                ),
                milestones=[],
            )

            linear_segments.append(segment)
            current_distance = end_distance
            segment_id += 1

        logger.info(f"Created {len(linear_segments)} linear segments from route")
        return linear_segments

    def extract_search_points_from_segments(
        self, segments: List[LinearRoadSegment]
    ) -> List[Tuple[Tuple[float, float], float]]:
        """
        Extract search points from segment start/end coordinates.

        These points are used for POI discovery along the route.
        Each segment's start point becomes a search point, plus
        the end point of the last segment.

        Args:
            segments: List of LinearRoadSegment objects

        Returns:
            List of tuples: ((lat, lon), distance_from_origin_km)
        """
        search_points = []

        for segment in segments:
            # Add segment start point
            if segment.start_coordinates:
                search_points.append(
                    (
                        (
                            segment.start_coordinates.latitude,
                            segment.start_coordinates.longitude,
                        ),
                        segment.start_distance_km,
                    )
                )

            # Add segment end point (only for last segment to avoid duplicates)
            if segment.end_coordinates and segment == segments[-1]:
                search_points.append(
                    (
                        (
                            segment.end_coordinates.latitude,
                            segment.end_coordinates.longitude,
                        ),
                        segment.end_distance_km,
                    )
                )

        return search_points


# Module-level instance for convenience
_default_service = RouteSegmentationService()


def process_route_into_segments(
    route: Route, segment_length_km: float = 1.0
) -> List[LinearRoadSegment]:
    """Process route into linear segments."""
    return _default_service.process_route_into_segments(route, segment_length_km)


def extract_search_points_from_segments(
    segments: List[LinearRoadSegment],
) -> List[Tuple[Tuple[float, float], float]]:
    """Extract search points from segments."""
    return _default_service.extract_search_points_from_segments(segments)
