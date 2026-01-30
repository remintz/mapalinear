"""
Tests for JunctionCalculationService.

Tests the junction calculation service including:
- Aggregating search points from segments
- Finding lookback points
- Calculating junction coordinates and side
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.services.junction_calculation_service import (
    GlobalSearchPoint,
    JunctionCalculationService,
    JunctionResult,
)


class TestGlobalSearchPoint:
    """Tests for the GlobalSearchPoint dataclass."""

    def test_basic_creation(self):
        """Test creating a GlobalSearchPoint."""
        sp = GlobalSearchPoint(
            lat=-23.5505,
            lon=-46.6333,
            segment_id=uuid4(),
            segment_sp_index=0,
            distance_from_map_origin_km=5.0,
        )

        assert sp.lat == -23.5505
        assert sp.lon == -46.6333
        assert sp.segment_sp_index == 0
        assert sp.distance_from_map_origin_km == 5.0


class TestJunctionResult:
    """Tests for the JunctionResult dataclass."""

    def test_basic_creation(self):
        """Test creating a JunctionResult."""
        result = JunctionResult(
            junction_lat=-23.5505,
            junction_lon=-46.6333,
            junction_distance_km=10.5,
            side="left",
            access_distance_km=0.5,
            requires_detour=False,
        )

        assert result.junction_lat == -23.5505
        assert result.junction_lon == -46.6333
        assert result.junction_distance_km == 10.5
        assert result.side == "left"
        assert result.access_distance_km == 0.5
        assert result.requires_detour is False


class TestAggregateSearchPoints:
    """Tests for the aggregate_search_points method."""

    @pytest.fixture
    def junction_service(self):
        return JunctionCalculationService()

    def test_empty_map_segments(self, junction_service):
        """Test with empty map segments list."""
        result = junction_service.aggregate_search_points([], {})
        assert result == []

    def test_single_segment_with_search_points(self, junction_service):
        """Test aggregation with a single segment."""
        segment_id = uuid4()

        # Create mock MapSegment
        map_segment = MagicMock()
        map_segment.segment_id = segment_id
        map_segment.distance_from_origin_km = Decimal("0.0")

        # Create mock RouteSegment with search points
        route_segment = MagicMock()
        route_segment.id = segment_id
        route_segment.search_points = [
            {"lat": -23.5505, "lon": -46.6333, "index": 0, "distance_from_segment_start_km": 0.0},
            {"lat": -23.5600, "lon": -46.6400, "index": 1, "distance_from_segment_start_km": 1.0},
            {"lat": -23.5700, "lon": -46.6500, "index": 2, "distance_from_segment_start_km": 2.0},
        ]

        segments_dict = {segment_id: route_segment}

        result = junction_service.aggregate_search_points([map_segment], segments_dict)

        assert len(result) == 3
        assert result[0].segment_sp_index == 0
        assert result[0].distance_from_map_origin_km == 0.0
        assert result[1].distance_from_map_origin_km == 1.0
        assert result[2].distance_from_map_origin_km == 2.0

    def test_multiple_segments_with_cumulative_distance(self, junction_service):
        """Test that distances are cumulative across segments."""
        segment1_id = uuid4()
        segment2_id = uuid4()

        # First segment starts at 0km
        map_segment1 = MagicMock()
        map_segment1.segment_id = segment1_id
        map_segment1.distance_from_origin_km = Decimal("0.0")

        route_segment1 = MagicMock()
        route_segment1.id = segment1_id
        route_segment1.search_points = [
            {"lat": -23.5505, "lon": -46.6333, "index": 0, "distance_from_segment_start_km": 0.0},
            {"lat": -23.5600, "lon": -46.6400, "index": 1, "distance_from_segment_start_km": 1.0},
        ]

        # Second segment starts at 5km
        map_segment2 = MagicMock()
        map_segment2.segment_id = segment2_id
        map_segment2.distance_from_origin_km = Decimal("5.0")

        route_segment2 = MagicMock()
        route_segment2.id = segment2_id
        route_segment2.search_points = [
            {"lat": -23.6000, "lon": -46.6600, "index": 0, "distance_from_segment_start_km": 0.0},
            {"lat": -23.6100, "lon": -46.6700, "index": 1, "distance_from_segment_start_km": 1.0},
        ]

        segments_dict = {segment1_id: route_segment1, segment2_id: route_segment2}

        result = junction_service.aggregate_search_points(
            [map_segment1, map_segment2], segments_dict
        )

        assert len(result) == 4
        # First segment SPs
        assert result[0].distance_from_map_origin_km == 0.0
        assert result[1].distance_from_map_origin_km == 1.0
        # Second segment SPs (should be 5.0 + local distance)
        assert result[2].distance_from_map_origin_km == 5.0
        assert result[3].distance_from_map_origin_km == 6.0

    def test_results_sorted_by_distance(self, junction_service):
        """Test that results are sorted by distance from origin."""
        segment1_id = uuid4()
        segment2_id = uuid4()

        # Create segments in reverse order (second segment first)
        map_segment1 = MagicMock()
        map_segment1.segment_id = segment1_id
        map_segment1.distance_from_origin_km = Decimal("10.0")

        route_segment1 = MagicMock()
        route_segment1.id = segment1_id
        route_segment1.search_points = [
            {"lat": -23.5505, "lon": -46.6333, "index": 0, "distance_from_segment_start_km": 0.0},
        ]

        map_segment2 = MagicMock()
        map_segment2.segment_id = segment2_id
        map_segment2.distance_from_origin_km = Decimal("0.0")

        route_segment2 = MagicMock()
        route_segment2.id = segment2_id
        route_segment2.search_points = [
            {"lat": -23.6000, "lon": -46.6600, "index": 0, "distance_from_segment_start_km": 0.0},
        ]

        segments_dict = {segment1_id: route_segment1, segment2_id: route_segment2}

        # Pass in non-sorted order
        result = junction_service.aggregate_search_points(
            [map_segment1, map_segment2], segments_dict
        )

        assert len(result) == 2
        # Should be sorted by distance
        assert result[0].distance_from_map_origin_km == 0.0
        assert result[1].distance_from_map_origin_km == 10.0


class TestFindLookbackPoint:
    """Tests for the find_lookback_point method."""

    @pytest.fixture
    def junction_service(self):
        return JunctionCalculationService()

    @pytest.fixture
    def sample_search_points(self):
        """Create sample search points for testing."""
        return [
            GlobalSearchPoint(
                lat=-23.5505, lon=-46.6333, segment_id=uuid4(),
                segment_sp_index=0, distance_from_map_origin_km=0.0
            ),
            GlobalSearchPoint(
                lat=-23.5600, lon=-46.6400, segment_id=uuid4(),
                segment_sp_index=1, distance_from_map_origin_km=5.0
            ),
            GlobalSearchPoint(
                lat=-23.5700, lon=-46.6500, segment_id=uuid4(),
                segment_sp_index=2, distance_from_map_origin_km=10.0
            ),
            GlobalSearchPoint(
                lat=-23.5800, lon=-46.6600, segment_id=uuid4(),
                segment_sp_index=3, distance_from_map_origin_km=15.0
            ),
            GlobalSearchPoint(
                lat=-23.5900, lon=-46.6700, segment_id=uuid4(),
                segment_sp_index=4, distance_from_map_origin_km=20.0
            ),
        ]

    def test_empty_search_points_returns_none(self, junction_service):
        """Test that empty search points returns None."""
        result = junction_service.find_lookback_point(15.0, [])
        assert result is None

    def test_poi_near_origin_returns_first_point(self, junction_service, sample_search_points):
        """Test that POI near origin returns first search point."""
        # POI at 5km, lookback 10km would be -5km, so return first point
        result = junction_service.find_lookback_point(5.0, sample_search_points)
        assert result == sample_search_points[0]

    def test_poi_at_origin_returns_first_point(self, junction_service, sample_search_points):
        """Test that POI at origin returns first search point."""
        result = junction_service.find_lookback_point(0.0, sample_search_points)
        assert result == sample_search_points[0]

    def test_normal_lookback(self, junction_service, sample_search_points):
        """Test normal lookback calculation."""
        # POI at 20km, lookback 10km = target at 10km
        # Should return the SP at 10km (index 2)
        result = junction_service.find_lookback_point(20.0, sample_search_points)
        assert result.distance_from_map_origin_km == 10.0

    def test_lookback_finds_last_point_before_target(self, junction_service, sample_search_points):
        """Test that lookback finds the last SP before target distance."""
        # POI at 18km, lookback 10km = target at 8km
        # Should return SP at 5km (index 1), the last one <= 8km
        result = junction_service.find_lookback_point(18.0, sample_search_points)
        assert result.distance_from_map_origin_km == 5.0

    def test_custom_lookback_distance(self, junction_service, sample_search_points):
        """Test with custom lookback distance."""
        # POI at 20km, lookback 5km = target at 15km
        # Should return SP at 15km (index 3)
        result = junction_service.find_lookback_point(
            20.0, sample_search_points, lookback_km=5.0
        )
        assert result.distance_from_map_origin_km == 15.0


class TestDetermineSide:
    """Tests for the _determine_side method."""

    @pytest.fixture
    def junction_service(self):
        return JunctionCalculationService()

    def test_poi_on_left_side(self, junction_service):
        """Test detection of POI on left side of road."""
        # Route going north (positive lat direction)
        route_geometry = [
            (-23.6000, -46.6500),
            (-23.5500, -46.6500),  # North direction
        ]
        junction = (-23.5750, -46.6500)
        # POI to the west (left when going north)
        poi = (-23.5750, -46.6600)

        result = junction_service._determine_side(
            poi_lat=poi[0],
            poi_lon=poi[1],
            junction=junction,
            route_geometry=route_geometry,
        )

        assert result == "left"

    def test_poi_on_right_side(self, junction_service):
        """Test detection of POI on right side of road."""
        # Route going north
        route_geometry = [
            (-23.6000, -46.6500),
            (-23.5500, -46.6500),
        ]
        junction = (-23.5750, -46.6500)
        # POI to the east (right when going north)
        poi = (-23.5750, -46.6400)

        result = junction_service._determine_side(
            poi_lat=poi[0],
            poi_lon=poi[1],
            junction=junction,
            route_geometry=route_geometry,
        )

        assert result == "right"

    def test_poi_on_route_returns_center(self, junction_service):
        """Test that POI exactly on route returns center."""
        route_geometry = [
            (-23.6000, -46.6500),
            (-23.5500, -46.6500),
        ]
        junction = (-23.5750, -46.6500)
        # POI exactly on the route
        poi = (-23.5750, -46.6500)

        result = junction_service._determine_side(
            poi_lat=poi[0],
            poi_lon=poi[1],
            junction=junction,
            route_geometry=route_geometry,
        )

        assert result == "center"

    def test_insufficient_geometry_returns_center(self, junction_service):
        """Test that insufficient geometry returns center."""
        route_geometry = [(-23.6000, -46.6500)]  # Only one point
        junction = (-23.5750, -46.6500)
        poi = (-23.5750, -46.6400)

        result = junction_service._determine_side(
            poi_lat=poi[0],
            poi_lon=poi[1],
            junction=junction,
            route_geometry=route_geometry,
        )

        assert result == "center"


class TestDetermineSideFromAccessRoute:
    """Tests for the _determine_side_from_access_route method."""

    @pytest.fixture
    def junction_service(self):
        return JunctionCalculationService()

    def test_access_route_going_left(self, junction_service):
        """Test detection of access route going left from main route."""
        # Main route going south (latitude decreasing)
        main_route = [
            (-20.20, -43.80),  # North
            (-20.22, -43.80),  # Junction area
            (-20.24, -43.80),  # South
        ]
        junction = (-20.22, -43.80)

        # Access route going west (left when traveling south)
        access_route = [
            (-20.20, -43.80),  # Start on main route
            (-20.22, -43.80),  # Junction
            (-20.22, -43.81),  # 50m west (turning left)
            (-20.22, -43.82),  # Further west
        ]

        result = junction_service._determine_side_from_access_route(
            junction, access_route, main_route
        )

        # When going south, west is RIGHT (not left!)
        assert result == "right"

    def test_access_route_going_right(self, junction_service):
        """Test detection of access route going right from main route."""
        # Main route going south
        main_route = [
            (-20.20, -43.80),
            (-20.22, -43.80),
            (-20.24, -43.80),
        ]
        junction = (-20.22, -43.80)

        # Access route going east (right when traveling south)
        access_route = [
            (-20.20, -43.80),
            (-20.22, -43.80),  # Junction
            (-20.22, -43.79),  # 50m east (turning right)
            (-20.22, -43.78),
        ]

        result = junction_service._determine_side_from_access_route(
            junction, access_route, main_route
        )

        # When going south, east is LEFT
        assert result == "left"

    def test_access_route_insufficient_geometry(self, junction_service):
        """Test with insufficient access route geometry."""
        main_route = [
            (-20.20, -43.80),
            (-20.24, -43.80),
        ]
        junction = (-20.22, -43.80)

        # Access route too short
        access_route = [(-20.22, -43.80)]

        result = junction_service._determine_side_from_access_route(
            junction, access_route, main_route
        )

        assert result == "center"

    def test_real_itabirito_scenario(self, junction_service):
        """Test with real-world Itabirito coordinates scenario.

        Route going south on BR-040, Itabirito to the west.
        Access route should turn RIGHT (west when heading south).
        """
        # Main route going south (based on debug data)
        # Start: -20.220358, -43.801619
        # End: -20.223029, -43.801783
        main_route = [
            (-20.218, -43.8015),  # Before junction
            (-20.220358, -43.801619),  # Segment start
            (-20.220581, -43.801627),  # Junction
            (-20.223029, -43.801783),  # Segment end
            (-20.226, -43.802),  # After junction
        ]
        junction = (-20.220581, -43.801627)

        # Access route that goes west (towards Itabirito)
        # Simulating a realistic exit that turns west
        access_route = [
            (-20.218, -43.8015),  # Before junction (on main route)
            (-20.220, -43.8016),  # Near junction
            (-20.220581, -43.801627),  # Junction point
            (-20.2206, -43.8025),  # ~100m west (turning right when going south)
            (-20.2208, -43.8035),  # Further west
            (-20.251972, -43.802917),  # Itabirito POI
        ]

        result = junction_service._determine_side_from_access_route(
            junction, access_route, main_route
        )

        # When going south, turning west is RIGHT
        assert result == "right"


class TestFindClosestRoutePoint:
    """Tests for the _find_closest_route_point method."""

    @pytest.fixture
    def junction_service(self):
        return JunctionCalculationService()

    def test_empty_geometry_returns_poi_location(self, junction_service):
        """Test that empty geometry returns the POI location."""
        result = junction_service._find_closest_route_point(
            lat=-23.5505,
            lon=-46.6333,
            route_geometry=[],
        )

        assert result == (-23.5505, -46.6333)

    def test_finds_closest_point(self, junction_service):
        """Test finding the closest point on route."""
        route_geometry = [
            (-23.5000, -46.6000),
            (-23.5500, -46.6500),  # This should be closest
            (-23.6000, -46.7000),
        ]

        result = junction_service._find_closest_route_point(
            lat=-23.5510,
            lon=-46.6510,
            route_geometry=route_geometry,
        )

        assert result == (-23.5500, -46.6500)

    def test_exact_match_returns_point(self, junction_service):
        """Test that exact match returns the point."""
        route_geometry = [
            (-23.5000, -46.6000),
            (-23.5500, -46.6500),
            (-23.6000, -46.7000),
        ]

        result = junction_service._find_closest_route_point(
            lat=-23.5500,
            lon=-46.6500,
            route_geometry=route_geometry,
        )

        assert result == (-23.5500, -46.6500)


class TestCalculateDistanceAlongRoute:
    """Tests for the _calculate_distance_along_route method."""

    @pytest.fixture
    def junction_service(self):
        return JunctionCalculationService()

    def test_empty_geometry_returns_zero(self, junction_service):
        """Test that empty geometry returns 0."""
        result = junction_service._calculate_distance_along_route(
            point=(-23.5505, -46.6333),
            route_geometry=[],
            route_total_km=100.0,
        )

        assert result == 0.0

    def test_first_point_returns_zero(self, junction_service):
        """Test that first point returns 0 distance."""
        route_geometry = [
            (-23.5000, -46.6000),
            (-23.5500, -46.6500),
            (-23.6000, -46.7000),
        ]

        result = junction_service._calculate_distance_along_route(
            point=(-23.5000, -46.6000),
            route_geometry=route_geometry,
            route_total_km=100.0,
        )

        assert result == 0.0

    def test_distance_increases_along_route(self, junction_service):
        """Test that distance increases as we move along route."""
        route_geometry = [
            (-23.5000, -46.6000),
            (-23.5500, -46.6500),
            (-23.6000, -46.7000),
        ]

        dist1 = junction_service._calculate_distance_along_route(
            point=(-23.5000, -46.6000),
            route_geometry=route_geometry,
            route_total_km=100.0,
        )

        dist2 = junction_service._calculate_distance_along_route(
            point=(-23.5500, -46.6500),
            route_geometry=route_geometry,
            route_total_km=100.0,
        )

        dist3 = junction_service._calculate_distance_along_route(
            point=(-23.6000, -46.7000),
            route_geometry=route_geometry,
            route_total_km=100.0,
        )

        assert dist1 < dist2 < dist3


class TestCalculateJunction:
    """Tests for the calculate_junction method."""

    @pytest.fixture
    def junction_service(self):
        return JunctionCalculationService()

    @pytest.fixture
    def sample_data(self):
        """Create sample data for junction calculation."""
        segment_id = uuid4()

        segment_poi = MagicMock()
        segment_poi.segment_id = segment_id
        segment_poi.search_point_index = 5
        segment_poi.straight_line_distance_m = 300

        map_segment = MagicMock()
        map_segment.distance_from_origin_km = Decimal("10.0")
        map_segment.sequence_order = 2

        route_geometry = [
            (-23.5000, -46.6000),
            (-23.5500, -46.6500),
            (-23.6000, -46.7000),
        ]

        global_sps = [
            GlobalSearchPoint(
                lat=-23.5000, lon=-46.6000, segment_id=segment_id,
                segment_sp_index=0, distance_from_map_origin_km=0.0
            ),
            GlobalSearchPoint(
                lat=-23.5500, lon=-46.6500, segment_id=segment_id,
                segment_sp_index=5, distance_from_map_origin_km=15.0
            ),
        ]

        return {
            "segment_poi": segment_poi,
            "map_segment": map_segment,
            "route_geometry": route_geometry,
            "route_total_km": 20.0,
            "global_sps": global_sps,
        }

    @pytest.mark.asyncio
    async def test_nearby_poi_returns_simple_junction(self, junction_service, sample_data):
        """Test that nearby POI (<500m) returns simple junction without routing."""
        result = await junction_service.calculate_junction(
            poi_lat=-23.5505,
            poi_lon=-46.6505,
            segment_poi=sample_data["segment_poi"],
            map_segment=sample_data["map_segment"],
            route_geometry=sample_data["route_geometry"],
            route_total_km=sample_data["route_total_km"],
            global_sps=sample_data["global_sps"],
        )

        assert isinstance(result, JunctionResult)
        assert result.requires_detour is False
        # Access distance should be approximately the straight line distance / 1000
        assert result.access_distance_km < 1.0

    @pytest.mark.asyncio
    async def test_distant_poi_without_provider_returns_none(
        self, junction_service, sample_data
    ):
        """Test that distant POI without geo provider returns None (no fallback)."""
        # Create segment_poi with large distance
        sample_data["segment_poi"].straight_line_distance_m = 2000

        result = await junction_service.calculate_junction(
            poi_lat=-23.5700,
            poi_lon=-46.6700,
            segment_poi=sample_data["segment_poi"],
            map_segment=sample_data["map_segment"],
            route_geometry=sample_data["route_geometry"],
            route_total_km=sample_data["route_total_km"],
            global_sps=sample_data["global_sps"],
        )

        # Without geo_provider, distant POIs cannot calculate access route and return None
        assert result is None

    @pytest.mark.asyncio
    async def test_junction_has_valid_coordinates(self, junction_service, sample_data):
        """Test that junction result has valid coordinates."""
        result = await junction_service.calculate_junction(
            poi_lat=-23.5505,
            poi_lon=-46.6505,
            segment_poi=sample_data["segment_poi"],
            map_segment=sample_data["map_segment"],
            route_geometry=sample_data["route_geometry"],
            route_total_km=sample_data["route_total_km"],
            global_sps=sample_data["global_sps"],
        )

        assert -90 <= result.junction_lat <= 90
        assert -180 <= result.junction_lon <= 180
        assert result.junction_distance_km >= 0
        assert result.side in ["left", "right", "center"]
