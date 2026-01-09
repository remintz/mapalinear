"""
Junction Calculation Service - Calculates junction points and side for POIs.

This service handles:
- Aggregating search points from map segments (global context)
- Finding lookback points for junction calculation
- Calculating junction coordinates, side, and access distance
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from api.database.models.map_segment import MapSegment
from api.database.models.route_segment import RouteSegment
from api.database.models.segment_poi import SegmentPOI
from api.providers.base import GeoProvider
from api.providers.models import GeoLocation, Route
from api.utils.geo_utils import (
    calculate_distance_meters,
    interpolate_coordinate_at_distance,
)

logger = logging.getLogger(__name__)


@dataclass
class GlobalSearchPoint:
    """
    A search point with global (map-level) distance information.

    Attributes:
        lat: Latitude
        lon: Longitude
        segment_id: ID of the segment containing this search point
        segment_sp_index: Index of this search point within its segment
        distance_from_map_origin_km: Distance from the map origin
    """
    lat: float
    lon: float
    segment_id: UUID
    segment_sp_index: int
    distance_from_map_origin_km: float


@dataclass
class JunctionResult:
    """
    Result of junction calculation for a POI.

    Attributes:
        junction_lat: Latitude of junction point
        junction_lon: Longitude of junction point
        junction_distance_km: Distance from map origin to junction
        side: Side of road ("left", "right", "center")
        access_distance_km: Distance from junction to POI
        requires_detour: Whether reaching this POI requires leaving the route
        access_route_geometry: Geometry of access route from lookback to POI
    """
    junction_lat: float
    junction_lon: float
    junction_distance_km: float
    side: str
    access_distance_km: float
    requires_detour: bool
    access_route_geometry: Optional[List[Tuple[float, float]]] = None


class JunctionCalculationService:
    """
    Service for calculating junction points and side determination for POIs.

    This service handles the context-dependent calculations that require
    knowledge of the full map route, such as:
    - Finding the optimal junction point (with 10km lookback)
    - Determining which side of the road a POI is on
    - Calculating access route distance
    """

    # Default lookback distance in km for junction calculation
    DEFAULT_LOOKBACK_KM = 10.0

    # Threshold distance in meters for "nearby" POIs that don't need junction
    NEARBY_THRESHOLD_M = 500

    def __init__(self, geo_provider: Optional[GeoProvider] = None):
        """
        Initialize the Junction Calculation Service.

        Args:
            geo_provider: Geographic provider for routing (optional, for access routes)
        """
        self.geo_provider = geo_provider

    def aggregate_search_points(
        self,
        map_segments: List[MapSegment],
        segments: Dict[UUID, RouteSegment],
    ) -> List[GlobalSearchPoint]:
        """
        Aggregate search points from all segments with global distances.

        Takes the pre-computed search points from each segment and adds
        the cumulative distance from map origin based on segment ordering.

        Args:
            map_segments: List of MapSegment (ordered by sequence)
            segments: Dict mapping segment_id to RouteSegment

        Returns:
            List of GlobalSearchPoint with absolute distances from map origin
        """
        global_sps: List[GlobalSearchPoint] = []

        for map_segment in map_segments:
            segment = segments.get(map_segment.segment_id)
            if not segment:
                continue

            segment_start_km = float(map_segment.distance_from_origin_km)

            for sp in segment.search_points or []:
                global_sp = GlobalSearchPoint(
                    lat=sp["lat"],
                    lon=sp["lon"],
                    segment_id=segment.id,
                    segment_sp_index=sp["index"],
                    distance_from_map_origin_km=segment_start_km + sp["distance_from_segment_start_km"],
                )
                global_sps.append(global_sp)

        # Sort by distance from origin
        global_sps.sort(key=lambda sp: sp.distance_from_map_origin_km)

        return global_sps

    def find_lookback_point(
        self,
        poi_distance_km: float,
        global_sps: List[GlobalSearchPoint],
        lookback_km: float = DEFAULT_LOOKBACK_KM,
    ) -> Optional[GlobalSearchPoint]:
        """
        Find the search point that is at least lookback_km before the POI.

        Args:
            poi_distance_km: Distance from map origin to POI (approximate)
            global_sps: List of GlobalSearchPoint sorted by distance
            lookback_km: How far back to look (default 10km)

        Returns:
            GlobalSearchPoint at least lookback_km before POI, or first SP if none
        """
        if not global_sps:
            return None

        target_distance = poi_distance_km - lookback_km

        # If target is before the route start, return first point
        if target_distance <= 0:
            return global_sps[0]

        # Find the last search point that is at or before target distance
        best_sp = global_sps[0]
        for sp in global_sps:
            if sp.distance_from_map_origin_km <= target_distance:
                best_sp = sp
            else:
                break

        return best_sp

    async def calculate_junction(
        self,
        poi_lat: float,
        poi_lon: float,
        segment_poi: SegmentPOI,
        map_segment: MapSegment,
        route_geometry: List[Tuple[float, float]],
        route_total_km: float,
        global_sps: List[GlobalSearchPoint],
    ) -> Optional[JunctionResult]:
        """
        Calculate junction point, side, and access distance for a POI.

        This method determines:
        1. The optimal point on the route to turn off to reach the POI
        2. Whether the POI is on the left or right side of the road
        3. The access route distance

        Args:
            poi_lat: POI latitude
            poi_lon: POI longitude
            segment_poi: SegmentPOI association with discovery data
            map_segment: MapSegment with segment position in map
            route_geometry: Full route geometry as [(lat, lon), ...]
            route_total_km: Total route length in km
            global_sps: All search points with global distances

        Returns:
            JunctionResult with calculated junction data, or None if calculation fails
        """
        # Calculate approximate POI distance from origin
        segment_start_km = float(map_segment.distance_from_origin_km)
        sp_index = segment_poi.search_point_index
        straight_line_distance_m = segment_poi.straight_line_distance_m

        # Find the search point that discovered this POI
        discovery_sp = None
        for sp in global_sps:
            if (sp.segment_id == segment_poi.segment_id and
                sp.segment_sp_index == sp_index):
                discovery_sp = sp
                break

        if not discovery_sp:
            # Estimate POI distance based on segment start + search point index
            poi_approx_distance_km = segment_start_km + (sp_index * 1.0)  # 1km per SP
        else:
            poi_approx_distance_km = discovery_sp.distance_from_map_origin_km

        # Check if POI is close enough to not need access route calculation
        if straight_line_distance_m <= self.NEARBY_THRESHOLD_M:
            # For nearby POIs, junction is the closest point on route
            junction_coords = self._find_closest_route_point(
                poi_lat, poi_lon, route_geometry
            )
            junction_distance_km = self._calculate_distance_along_route(
                junction_coords, route_geometry, route_total_km
            )
            side = self._determine_side(
                poi_lat, poi_lon, junction_coords, route_geometry
            )

            return JunctionResult(
                junction_lat=junction_coords[0],
                junction_lon=junction_coords[1],
                junction_distance_km=junction_distance_km,
                side=side,
                access_distance_km=straight_line_distance_m / 1000.0,
                requires_detour=False,
            )

        # For distant POIs, must calculate access route
        lookback_sp = self.find_lookback_point(
            poi_approx_distance_km, global_sps, self.DEFAULT_LOOKBACK_KM
        )

        if not lookback_sp:
            logger.warning(f"No lookback point found for POI at ({poi_lat}, {poi_lon})")
            return None

        lookback_coords = (lookback_sp.lat, lookback_sp.lon)

        # Calculate junction using routing - required for distant POIs
        junction_result = await self._calculate_junction_with_routing(
            poi_lat, poi_lon,
            lookback_coords,
            route_geometry,
            route_total_km,
        )

        if not junction_result:
            logger.warning(
                f"Failed to calculate access route for POI at ({poi_lat}, {poi_lon})"
            )
            return None

        return junction_result

    def _find_closest_route_point(
        self,
        lat: float,
        lon: float,
        route_geometry: List[Tuple[float, float]],
    ) -> Tuple[float, float]:
        """Find the closest point on the route to given coordinates."""
        if not route_geometry:
            return (lat, lon)

        best_point = route_geometry[0]
        best_distance = float('inf')

        for point in route_geometry:
            distance = calculate_distance_meters(lat, lon, point[0], point[1])
            if distance < best_distance:
                best_distance = distance
                best_point = point

        return best_point

    def _calculate_distance_along_route(
        self,
        point: Tuple[float, float],
        route_geometry: List[Tuple[float, float]],
        route_total_km: float,
    ) -> float:
        """Calculate distance from route start to a point on the route."""
        if not route_geometry:
            return 0.0

        # Find the closest segment and calculate cumulative distance
        cumulative_distance = 0.0
        best_match_distance = 0.0
        best_match_cumulative = 0.0

        for i, route_point in enumerate(route_geometry):
            if i > 0:
                prev = route_geometry[i - 1]
                segment_dist = calculate_distance_meters(
                    prev[0], prev[1], route_point[0], route_point[1]
                )
                cumulative_distance += segment_dist / 1000.0

            point_dist = calculate_distance_meters(
                point[0], point[1], route_point[0], route_point[1]
            )

            if i == 0 or point_dist < best_match_distance:
                best_match_distance = point_dist
                best_match_cumulative = cumulative_distance

        return best_match_cumulative

    def _determine_side(
        self,
        poi_lat: float,
        poi_lon: float,
        junction: Tuple[float, float],
        route_geometry: List[Tuple[float, float]],
    ) -> str:
        """
        Determine if POI is on left or right side of the road.

        Uses cross product to determine side relative to travel direction.
        """
        if not route_geometry or len(route_geometry) < 2:
            return "center"

        # Find the junction index in route
        junction_idx = 0
        best_dist = float('inf')
        for i, point in enumerate(route_geometry):
            dist = calculate_distance_meters(
                junction[0], junction[1], point[0], point[1]
            )
            if dist < best_dist:
                best_dist = dist
                junction_idx = i

        # Get direction vector (from previous point to next point)
        prev_idx = max(0, junction_idx - 1)
        next_idx = min(len(route_geometry) - 1, junction_idx + 1)

        if prev_idx == next_idx:
            return "center"

        # Direction vector
        dx = route_geometry[next_idx][1] - route_geometry[prev_idx][1]  # lon
        dy = route_geometry[next_idx][0] - route_geometry[prev_idx][0]  # lat

        # Vector from junction to POI
        px = poi_lon - junction[1]
        py = poi_lat - junction[0]

        # Cross product: dx * py - dy * px
        cross = dx * py - dy * px

        if abs(cross) < 1e-10:
            return "center"
        elif cross > 0:
            return "left"
        else:
            return "right"

    async def _calculate_junction_with_routing(
        self,
        poi_lat: float,
        poi_lon: float,
        lookback_coords: Tuple[float, float],
        route_geometry: List[Tuple[float, float]],
        route_total_km: float,
    ) -> Optional[JunctionResult]:
        """
        Calculate junction using actual routing to the POI.

        This method routes from the lookback point to the POI and finds
        where the access route intersects with the main route.
        """
        if not self.geo_provider:
            return None

        try:
            # Route from lookback point to POI
            origin = GeoLocation(
                latitude=lookback_coords[0],
                longitude=lookback_coords[1]
            )
            destination = GeoLocation(latitude=poi_lat, longitude=poi_lon)

            access_route = await self.geo_provider.calculate_route(
                origin, destination
            )

            if not access_route or not access_route.geometry:
                return None

            # Find intersection with main route
            junction_coords, junction_km = self._find_route_intersection(
                access_route.geometry,
                route_geometry,
                route_total_km,
            )

            if not junction_coords:
                return None

            # Determine side
            side = self._determine_side(
                poi_lat, poi_lon, junction_coords, route_geometry
            )

            # Access distance is from junction to POI along access route
            # For simplicity, use straight line since we don't have the exact
            # portion of access route after junction
            access_distance_km = calculate_distance_meters(
                junction_coords[0], junction_coords[1],
                poi_lat, poi_lon
            ) / 1000.0

            # Determine if detour is needed based on final access distance
            access_distance_m = access_distance_km * 1000
            requires_detour = access_distance_m > self.NEARBY_THRESHOLD_M

            return JunctionResult(
                junction_lat=junction_coords[0],
                junction_lon=junction_coords[1],
                junction_distance_km=junction_km,
                side=side,
                access_distance_km=access_distance_km,
                requires_detour=requires_detour,
                access_route_geometry=access_route.geometry,
            )

        except Exception as e:
            logger.warning(f"Failed to calculate junction with routing: {e}")
            return None

    def _find_route_intersection(
        self,
        access_geometry: List[Tuple[float, float]],
        main_geometry: List[Tuple[float, float]],
        main_total_km: float,
    ) -> Tuple[Optional[Tuple[float, float]], float]:
        """
        Find where access route intersects main route.

        Returns the intersection point and its distance along main route.
        """
        if not access_geometry or not main_geometry:
            return None, 0.0

        # Find the closest point on main route to any point on access route
        best_intersection = None
        best_distance = float('inf')
        best_main_distance_km = 0.0

        cumulative_distance = 0.0
        for i, main_point in enumerate(main_geometry):
            if i > 0:
                prev = main_geometry[i - 1]
                segment_dist = calculate_distance_meters(
                    prev[0], prev[1], main_point[0], main_point[1]
                )
                cumulative_distance += segment_dist / 1000.0

            for access_point in access_geometry:
                dist = calculate_distance_meters(
                    main_point[0], main_point[1],
                    access_point[0], access_point[1]
                )
                # Consider intersection if within 50m
                if dist < 50 and dist < best_distance:
                    best_distance = dist
                    best_intersection = main_point
                    best_main_distance_km = cumulative_distance

        return best_intersection, best_main_distance_km
