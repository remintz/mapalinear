"""
Unit tests for api/services/route_segmentation_service.py

Tests for route segmentation:
- process_route_into_segments
- extract_search_points_from_segments
"""

import pytest

from api.models.road_models import Coordinates, LinearRoadSegment
from api.providers.models import GeoLocation, Route
from api.services.route_segmentation_service import (
    RouteSegmentationService,
    process_route_into_segments,
    extract_search_points_from_segments,
)


class TestProcessRouteIntoSegments:
    """Tests for route segmentation."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return RouteSegmentationService()

    @pytest.fixture
    def sample_route(self):
        """Create a sample route for testing."""
        return Route(
            origin=GeoLocation(latitude=-23.55, longitude=-46.63),
            destination=GeoLocation(latitude=-23.65, longitude=-46.73),
            total_distance=10.0,  # 10 km
            total_duration=600,   # 10 minutes
            geometry=[
                (-23.55, -46.63),
                (-23.57, -46.65),
                (-23.59, -46.67),
                (-23.61, -46.69),
                (-23.63, -46.71),
                (-23.65, -46.73),
            ],
            road_names=["BR-116"],
        )

    def test_basic_segmentation(self, service, sample_route):
        """Route should be segmented into expected number of segments."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=1.0)
        # 10 km route with 1 km segments should have ~10 segments
        assert len(segments) == 10

    def test_segment_length_2km(self, service, sample_route):
        """2 km segments should result in half the number."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        assert len(segments) == 5

    def test_segment_length_5km(self, service, sample_route):
        """5 km segments should result in 2 segments."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=5.0)
        assert len(segments) == 2

    def test_segment_larger_than_route(self, service, sample_route):
        """Segment larger than route should result in 1 segment."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=20.0)
        assert len(segments) == 1

    def test_segments_have_correct_ids(self, service, sample_route):
        """Segments should have sequential IDs."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        for i, segment in enumerate(segments):
            assert segment.id == f"segment_{i + 1}"

    def test_segments_have_road_name(self, service, sample_route):
        """Segments should have road name from route."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        for segment in segments:
            assert segment.name == "BR-116"

    def test_segment_distances_are_continuous(self, service, sample_route):
        """Segment distances should be continuous."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        for i in range(len(segments) - 1):
            assert segments[i].end_distance_km == segments[i + 1].start_distance_km

    def test_first_segment_starts_at_zero(self, service, sample_route):
        """First segment should start at 0."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        assert segments[0].start_distance_km == 0.0

    def test_last_segment_ends_at_total(self, service, sample_route):
        """Last segment should end at total distance."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        assert segments[-1].end_distance_km == sample_route.total_distance

    def test_segments_have_coordinates(self, service, sample_route):
        """Segments should have start and end coordinates."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        for segment in segments:
            assert segment.start_coordinates is not None
            assert segment.end_coordinates is not None
            assert isinstance(segment.start_coordinates, Coordinates)
            assert isinstance(segment.end_coordinates, Coordinates)

    def test_segments_have_correct_length(self, service, sample_route):
        """Segments should have correct length calculated."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        for segment in segments:
            expected_length = segment.end_distance_km - segment.start_distance_km
            assert segment.length_km == expected_length

    def test_segments_start_with_empty_milestones(self, service, sample_route):
        """Segments should start with empty milestones list."""
        segments = service.process_route_into_segments(sample_route, segment_length_km=2.0)
        for segment in segments:
            assert segment.milestones == []

    def test_route_without_road_names(self, service):
        """Route without road names should use default name."""
        route = Route(
            origin=GeoLocation(latitude=-23.55, longitude=-46.63),
            destination=GeoLocation(latitude=-23.65, longitude=-46.73),
            total_distance=10.0,
            total_duration=600,
            geometry=[(-23.55, -46.63), (-23.65, -46.73)],
            road_names=[],
        )
        segments = service.process_route_into_segments(route, segment_length_km=5.0)
        assert segments[0].name == "Unnamed Road"


class TestExtractSearchPointsFromSegments:
    """Tests for extracting search points from segments."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return RouteSegmentationService()

    @pytest.fixture
    def sample_segments(self):
        """Create sample segments for testing."""
        return [
            LinearRoadSegment(
                id="segment_1",
                name="BR-116",
                start_distance_km=0.0,
                end_distance_km=5.0,
                length_km=5.0,
                start_coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                end_coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                milestones=[],
            ),
            LinearRoadSegment(
                id="segment_2",
                name="BR-116",
                start_distance_km=5.0,
                end_distance_km=10.0,
                length_km=5.0,
                start_coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                end_coordinates=Coordinates(latitude=-23.65, longitude=-46.73),
                milestones=[],
            ),
        ]

    def test_extracts_start_points(self, service, sample_segments):
        """Should extract start point of each segment."""
        points = service.extract_search_points_from_segments(sample_segments)
        # Should have start of each segment + end of last
        assert len(points) == 3

    def test_first_point_at_origin(self, service, sample_segments):
        """First point should be at route origin."""
        points = service.extract_search_points_from_segments(sample_segments)
        assert points[0] == ((-23.55, -46.63), 0.0)

    def test_last_point_at_destination(self, service, sample_segments):
        """Last point should be at route destination."""
        points = service.extract_search_points_from_segments(sample_segments)
        assert points[-1] == ((-23.65, -46.73), 10.0)

    def test_points_have_correct_distances(self, service, sample_segments):
        """Points should have correct distances from origin."""
        points = service.extract_search_points_from_segments(sample_segments)
        distances = [p[1] for p in points]
        assert distances == [0.0, 5.0, 10.0]

    def test_empty_segments_returns_empty(self, service):
        """Empty segments list should return empty list."""
        points = service.extract_search_points_from_segments([])
        assert points == []

    def test_single_segment(self, service):
        """Single segment should return 2 points (start + end)."""
        segments = [
            LinearRoadSegment(
                id="segment_1",
                name="BR-116",
                start_distance_km=0.0,
                end_distance_km=10.0,
                length_km=10.0,
                start_coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                end_coordinates=Coordinates(latitude=-23.65, longitude=-46.73),
                milestones=[],
            ),
        ]
        points = service.extract_search_points_from_segments(segments)
        assert len(points) == 2

    def test_segment_without_coordinates(self, service):
        """Segment without coordinates should be skipped."""
        segments = [
            LinearRoadSegment(
                id="segment_1",
                name="BR-116",
                start_distance_km=0.0,
                end_distance_km=10.0,
                length_km=10.0,
                start_coordinates=None,
                end_coordinates=None,
                milestones=[],
            ),
        ]
        points = service.extract_search_points_from_segments(segments)
        assert len(points) == 0


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def sample_route(self):
        """Create a sample route for testing."""
        return Route(
            origin=GeoLocation(latitude=-23.55, longitude=-46.63),
            destination=GeoLocation(latitude=-23.65, longitude=-46.73),
            total_distance=10.0,
            total_duration=600,
            geometry=[(-23.55, -46.63), (-23.65, -46.73)],
            road_names=["BR-116"],
        )

    def test_process_route_function(self, sample_route):
        """Module function should work like instance method."""
        segments = process_route_into_segments(sample_route, segment_length_km=5.0)
        assert len(segments) == 2

    def test_extract_points_function(self, sample_route):
        """Module function should work like instance method."""
        segments = process_route_into_segments(sample_route, segment_length_km=5.0)
        points = extract_search_points_from_segments(segments)
        assert len(points) == 3
