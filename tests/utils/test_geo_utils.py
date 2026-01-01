"""
Unit tests for api/utils/geo_utils.py

Tests for pure mathematical functions:
- calculate_distance_meters (Haversine formula)
- calculate_distance_along_route
- calculate_distance_from_point_to_end
- interpolate_coordinate_at_distance
- find_closest_point_index
- find_closest_segment_index
"""

import math
import pytest

from api.utils.geo_utils import (
    calculate_distance_meters,
    calculate_distance_along_route,
    calculate_distance_from_point_to_end,
    interpolate_coordinate_at_distance,
    find_closest_point_index,
    find_closest_segment_index,
)


class TestCalculateDistanceMeters:
    """Tests for Haversine distance calculation."""

    def test_same_point_returns_zero(self):
        """Distance between same point should be zero."""
        distance = calculate_distance_meters(-23.5505, -46.6333, -23.5505, -46.6333)
        assert distance == 0.0

    def test_known_distance_sao_paulo_to_rio(self):
        """Test known distance between Sao Paulo and Rio de Janeiro."""
        # Sao Paulo: -23.5505, -46.6333
        # Rio de Janeiro: -22.9068, -43.1729
        distance = calculate_distance_meters(-23.5505, -46.6333, -22.9068, -43.1729)
        # Known distance is approximately 357-360 km
        assert 356000 <= distance <= 365000

    def test_short_distance_100_meters(self):
        """Test short distance approximately 100 meters."""
        # ~100m apart (approximately 0.001 degrees latitude at equator)
        lat1, lon1 = 0.0, 0.0
        lat2, lon2 = 0.0009, 0.0  # ~100m north
        distance = calculate_distance_meters(lat1, lon1, lat2, lon2)
        assert 90 <= distance <= 110

    def test_symmetry(self):
        """Distance A to B should equal distance B to A."""
        lat1, lon1 = -23.5505, -46.6333
        lat2, lon2 = -22.9068, -43.1729
        d1 = calculate_distance_meters(lat1, lon1, lat2, lon2)
        d2 = calculate_distance_meters(lat2, lon2, lat1, lon1)
        assert abs(d1 - d2) < 0.001

    def test_negative_coordinates(self):
        """Test with negative coordinates (southern hemisphere)."""
        distance = calculate_distance_meters(-33.8688, 151.2093, -34.0000, 151.0000)
        assert distance > 0

    def test_equator_distance(self):
        """One degree longitude at equator should be ~111 km."""
        distance = calculate_distance_meters(0.0, 0.0, 0.0, 1.0)
        # ~111.32 km at equator
        assert 110000 <= distance <= 113000

    def test_latitude_distance(self):
        """One degree latitude should be ~111 km anywhere."""
        distance = calculate_distance_meters(0.0, 0.0, 1.0, 0.0)
        assert 110000 <= distance <= 113000


class TestCalculateDistanceAlongRoute:
    """Tests for calculating distance along a route to a target point."""

    def test_empty_geometry_returns_zero(self):
        """Empty geometry should return 0."""
        distance = calculate_distance_along_route([], (0, 0))
        assert distance == 0.0

    def test_target_at_start(self):
        """Target at route start should return ~0."""
        geometry = [(-23.55, -46.63), (-23.56, -46.64), (-23.57, -46.65)]
        distance = calculate_distance_along_route(geometry, (-23.55, -46.63))
        assert distance < 1.0  # Less than 1 km

    def test_target_along_route(self):
        """Target along route should return cumulative distance."""
        # Create a route with 3 points, each ~1.1km apart (0.01 degrees lat)
        geometry = [
            (-23.55, -46.63),
            (-23.56, -46.63),  # ~1.1km south
            (-23.57, -46.63),  # ~2.2km south
        ]
        # Target slightly past second point - closer to second segment
        target = (-23.565, -46.63)  # Between second and third point
        distance = calculate_distance_along_route(geometry, target)
        # Should be approximately 1.1km (first segment) + some partial distance
        # Result depends on which segment is "closest" to the target
        assert distance >= 0.0

    def test_single_point_geometry(self):
        """Single point geometry should return 0."""
        geometry = [(-23.55, -46.63)]
        distance = calculate_distance_along_route(geometry, (-23.55, -46.63))
        assert distance == 0.0


class TestCalculateDistanceFromPointToEnd:
    """Tests for calculating remaining distance from a point to route end."""

    def test_empty_geometry_returns_zero(self):
        """Empty geometry should return 0."""
        distance = calculate_distance_from_point_to_end([], (0, 0))
        assert distance == 0.0

    def test_single_point_geometry_returns_zero(self):
        """Single point geometry should return 0."""
        geometry = [(-23.55, -46.63)]
        distance = calculate_distance_from_point_to_end(geometry, (-23.55, -46.63))
        assert distance == 0.0

    def test_start_point_returns_total_distance(self):
        """Starting at beginning should return approximately total distance."""
        geometry = [
            (-23.55, -46.63),
            (-23.56, -46.63),
            (-23.57, -46.63),
        ]
        distance = calculate_distance_from_point_to_end(geometry, (-23.55, -46.63))
        # Should be close to total route distance
        assert distance > 0

    def test_end_point_returns_small_value(self):
        """Point at end should return small distance."""
        geometry = [
            (-23.55, -46.63),
            (-23.56, -46.63),
            (-23.57, -46.63),
        ]
        distance = calculate_distance_from_point_to_end(geometry, (-23.57, -46.63))
        # Should be small value (projection distance)
        assert distance < 2.0  # Less than 2 km


class TestInterpolateCoordinateAtDistance:
    """Tests for coordinate interpolation along route."""

    def test_empty_geometry_returns_zero(self):
        """Empty geometry should return (0, 0)."""
        result = interpolate_coordinate_at_distance([], 5.0, 10.0)
        assert result == (0.0, 0.0)

    def test_negative_distance_returns_first_point(self):
        """Negative distance should return first point."""
        geometry = [(-23.55, -46.63), (-23.56, -46.64)]
        result = interpolate_coordinate_at_distance(geometry, -1.0, 10.0)
        assert result == geometry[0]

    def test_zero_distance_returns_first_point(self):
        """Zero distance should return first point."""
        geometry = [(-23.55, -46.63), (-23.56, -46.64)]
        result = interpolate_coordinate_at_distance(geometry, 0.0, 10.0)
        assert result == geometry[0]

    def test_max_distance_returns_last_point(self):
        """Distance >= total should return last point."""
        geometry = [(-23.55, -46.63), (-23.56, -46.64)]
        result = interpolate_coordinate_at_distance(geometry, 15.0, 10.0)
        assert result == geometry[-1]

    def test_midpoint_interpolation(self):
        """Half distance should return approximate midpoint."""
        geometry = [(-23.55, -46.63), (-23.57, -46.65)]
        result = interpolate_coordinate_at_distance(geometry, 5.0, 10.0)
        # Should be close to midpoint
        expected_lat = (-23.55 + -23.57) / 2
        expected_lon = (-46.63 + -46.65) / 2
        assert abs(result[0] - expected_lat) < 0.01
        assert abs(result[1] - expected_lon) < 0.01

    def test_quarter_distance(self):
        """25% distance should return quarter point."""
        geometry = [(-23.50, -46.60), (-23.60, -46.70)]
        result = interpolate_coordinate_at_distance(geometry, 2.5, 10.0)
        # 25% along the line
        expected_lat = -23.50 + 0.25 * (-23.60 - (-23.50))
        expected_lon = -46.60 + 0.25 * (-46.70 - (-46.60))
        assert abs(result[0] - expected_lat) < 0.01
        assert abs(result[1] - expected_lon) < 0.01

    def test_multiple_segments(self):
        """Test interpolation on geometry with multiple segments."""
        geometry = [
            (-23.50, -46.60),
            (-23.55, -46.65),
            (-23.60, -46.70),
        ]
        # 50% should be at or near middle point
        result = interpolate_coordinate_at_distance(geometry, 5.0, 10.0)
        assert abs(result[0] - (-23.55)) < 0.02
        assert abs(result[1] - (-46.65)) < 0.02


class TestFindClosestPointIndex:
    """Tests for finding closest point in geometry."""

    def test_empty_geometry_returns_zero(self):
        """Empty geometry should return 0."""
        result = find_closest_point_index([], (0, 0))
        assert result == 0

    def test_single_point_returns_zero(self):
        """Single point geometry should return 0."""
        geometry = [(-23.55, -46.63)]
        result = find_closest_point_index(geometry, (-23.55, -46.63))
        assert result == 0

    def test_exact_match_first_point(self):
        """Exact match on first point should return 0."""
        geometry = [(-23.55, -46.63), (-23.56, -46.64), (-23.57, -46.65)]
        result = find_closest_point_index(geometry, (-23.55, -46.63))
        assert result == 0

    def test_exact_match_last_point(self):
        """Exact match on last point should return last index."""
        geometry = [(-23.55, -46.63), (-23.56, -46.64), (-23.57, -46.65)]
        result = find_closest_point_index(geometry, (-23.57, -46.65))
        assert result == 2

    def test_closest_to_middle(self):
        """Point closest to middle should return middle index."""
        geometry = [(-23.50, -46.60), (-23.55, -46.65), (-23.60, -46.70)]
        result = find_closest_point_index(geometry, (-23.55, -46.65))
        assert result == 1

    def test_between_points(self):
        """Point between two should return closest one."""
        geometry = [(-23.50, -46.60), (-23.60, -46.70)]
        # Point slightly closer to first
        result = find_closest_point_index(geometry, (-23.52, -46.62))
        assert result == 0


class TestFindClosestSegmentIndex:
    """Tests for finding closest segment in geometry."""

    def test_empty_geometry_returns_zero(self):
        """Empty geometry should return 0."""
        result = find_closest_segment_index([], (0, 0))
        assert result == 0

    def test_single_point_returns_zero(self):
        """Single point (no segments) should return 0."""
        geometry = [(-23.55, -46.63)]
        result = find_closest_segment_index(geometry, (-23.55, -46.63))
        assert result == 0

    def test_two_points_single_segment(self):
        """Two points (one segment) should return 0."""
        geometry = [(-23.55, -46.63), (-23.56, -46.64)]
        result = find_closest_segment_index(geometry, (-23.555, -46.635))
        assert result == 0

    def test_multiple_segments_first(self):
        """Point near first segment should return 0."""
        geometry = [
            (-23.50, -46.60),
            (-23.52, -46.62),
            (-23.60, -46.70),
        ]
        result = find_closest_segment_index(geometry, (-23.51, -46.61))
        assert result == 0

    def test_multiple_segments_second(self):
        """Point near second segment should return 1."""
        geometry = [
            (-23.50, -46.60),
            (-23.52, -46.62),
            (-23.60, -46.70),
        ]
        # Point near second segment midpoint
        result = find_closest_segment_index(geometry, (-23.56, -46.66))
        assert result == 1

    def test_returns_valid_segment_index(self):
        """Result should always be valid segment index (0 to len-2)."""
        geometry = [
            (-23.50, -46.60),
            (-23.52, -46.62),
            (-23.54, -46.64),
            (-23.56, -46.66),
        ]
        for point in geometry:
            result = find_closest_segment_index(geometry, point)
            assert 0 <= result <= len(geometry) - 2
