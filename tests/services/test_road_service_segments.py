"""
Integration tests for RoadService with Reusable Segments.

Tests the integration between RoadService, SegmentService, and MapAssemblyService
for the new segment-based architecture.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.services.road_service import RoadService
from api.services.segment_service import SegmentService
from api.providers.base import GeoProvider, ProviderType
from api.providers.models import GeoLocation, Route, RouteStep, POI, POICategory


class TestProcessStepsIntoSegments:
    """Tests for _process_steps_into_segments method."""

    @pytest.fixture
    def sample_route_steps(self):
        """Create sample RouteSteps from OSRM."""
        return [
            RouteStep(
                distance_m=5000.0,
                duration_s=300.0,
                geometry=[
                    (-23.5505, -46.6333),
                    (-23.5600, -46.6400),
                    (-23.5700, -46.6500),
                ],
                road_name="BR-116",
                maneuver_type="turn",
                maneuver_modifier="left",
                maneuver_location=(-23.5505, -46.6333),
            ),
            RouteStep(
                distance_m=8000.0,
                duration_s=480.0,
                geometry=[
                    (-23.5700, -46.6500),
                    (-23.6000, -46.7000),
                    (-23.6300, -46.7500),
                ],
                road_name="BR-116",
                maneuver_type="continue",
                maneuver_modifier=None,
                maneuver_location=(-23.5700, -46.6500),
            ),
            RouteStep(
                distance_m=3000.0,
                duration_s=180.0,
                geometry=[
                    (-23.6300, -46.7500),
                    (-23.6500, -46.7800),
                ],
                road_name="Via Dutra",
                maneuver_type="turn",
                maneuver_modifier="right",
                maneuver_location=(-23.6300, -46.7500),
            ),
        ]

    def test_route_steps_have_correct_properties(self, sample_route_steps):
        """Test that RouteSteps have all required properties for segment creation."""
        for step in sample_route_steps:
            # Each step should have start and end coordinates
            assert step.start_coords is not None
            assert step.end_coords is not None

            # Should have distance in km
            assert step.distance_km >= 0

            # Should have geometry
            assert len(step.geometry) >= 2

    def test_route_step_distance_conversion(self, sample_route_steps):
        """Test that distance_m is correctly converted to distance_km."""
        step = sample_route_steps[0]

        # 5000m should be 5km
        assert step.distance_m == 5000.0
        assert step.distance_km == 5.0

    def test_route_step_coordinates_extraction(self, sample_route_steps):
        """Test that start and end coordinates are extracted from geometry."""
        step = sample_route_steps[0]

        # Start coords should be first point of geometry
        assert step.start_coords == step.geometry[0]

        # End coords should be last point of geometry
        assert step.end_coords == step.geometry[-1]


class TestSegmentHashCalculation:
    """Tests for segment hash consistency across services."""

    def test_hash_is_consistent(self):
        """Test that segment hash is calculated consistently."""
        hash1 = SegmentService.calculate_segment_hash(
            start_lat=-23.5505,
            start_lon=-46.6333,
            end_lat=-23.5700,
            end_lon=-46.6500,
        )
        hash2 = SegmentService.calculate_segment_hash(
            start_lat=-23.5505,
            start_lon=-46.6333,
            end_lat=-23.5700,
            end_lon=-46.6500,
        )

        assert hash1 == hash2

    def test_hash_uses_4_decimal_precision(self):
        """Test that hash uses 4 decimal precision for matching."""
        # Coordinates that differ by less than 0.00005 should produce same hash
        hash1 = SegmentService.calculate_segment_hash(
            start_lat=-23.55050001,
            start_lon=-46.63330001,
            end_lat=-23.57000001,
            end_lon=-46.65000001,
        )
        hash2 = SegmentService.calculate_segment_hash(
            start_lat=-23.55050004,
            start_lon=-46.63330004,
            end_lat=-23.57000004,
            end_lon=-46.65000004,
        )

        assert hash1 == hash2


class TestSegmentReuse:
    """Tests for segment reuse functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def segment_service(self, mock_session):
        """Create SegmentService with mocked session."""
        return SegmentService(mock_session)

    @pytest.fixture
    def sample_step(self):
        """Create a sample RouteStep."""
        return RouteStep(
            distance_m=5000.0,
            duration_s=300.0,
            geometry=[(-23.5505, -46.6333), (-23.5700, -46.6500)],
            road_name="BR-116",
            maneuver_type="turn",
            maneuver_modifier="left",
            maneuver_location=(-23.5505, -46.6333),
        )

    @pytest.mark.asyncio
    async def test_creates_new_segment_when_not_exists(self, segment_service, sample_step):
        """Test that new segment is created when none exists."""
        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=None)
        segment_service.segment_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        segment, is_new = await segment_service.get_or_create_segment(sample_step)

        assert is_new is True
        segment_service.segment_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_existing_segment_when_exists(self, segment_service, sample_step):
        """Test that existing segment is returned when found."""
        existing_segment = MagicMock()
        existing_segment.id = uuid4()

        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=existing_segment)
        segment_service.segment_repo.increment_usage_count = AsyncMock()

        segment, is_new = await segment_service.get_or_create_segment(sample_step)

        assert is_new is False
        assert segment == existing_segment
        segment_service.segment_repo.increment_usage_count.assert_called_once_with(
            existing_segment.id
        )

    @pytest.mark.asyncio
    async def test_increments_usage_count_for_existing(self, segment_service, sample_step):
        """Test that usage count is incremented for existing segments."""
        existing_segment = MagicMock()
        existing_segment.id = uuid4()

        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=existing_segment)
        segment_service.segment_repo.increment_usage_count = AsyncMock()

        await segment_service.get_or_create_segment(sample_step)

        segment_service.segment_repo.increment_usage_count.assert_called_once()


class TestSearchPointGeneration:
    """Tests for search point generation in segments."""

    def test_generates_search_points_for_long_segment(self):
        """Test that search points are generated for segments >= 1km."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.5600, -46.6400),
            (-23.5700, -46.6500),
            (-23.5800, -46.6600),
        ]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=5.0,
        )

        assert len(search_points) >= 5  # At least every 1km

    def test_no_search_points_for_short_segment(self):
        """Test that no search points for segments < 1km."""
        geometry = [(-23.5505, -46.6333), (-23.5510, -46.6338)]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=0.5,
        )

        assert len(search_points) == 0

    def test_search_points_have_correct_structure(self):
        """Test that search points have correct structure."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.5800, -46.6600),
        ]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=5.0,
        )

        for sp in search_points:
            assert "index" in sp
            assert "lat" in sp
            assert "lon" in sp
            assert "distance_from_segment_start_km" in sp

    def test_search_points_are_sequential(self):
        """Test that search points have sequential indices."""
        geometry = [(-23.5505, -46.6333), (-23.6500, -46.7500)]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=15.0,
        )

        for i, sp in enumerate(search_points):
            assert sp["index"] == i


class TestPOIDeduplication:
    """Tests for POI deduplication across segments."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_deduplication_keeps_shorter_access(self, mock_session):
        """Test that deduplication keeps POI with shorter access distance."""
        from api.services.map_assembly_service import MapAssemblyService

        service = MapAssemblyService(mock_session)
        service.map_poi_repo.bulk_create = AsyncMock()

        poi_id = uuid4()
        segment_id = uuid4()

        # Create mock POI
        poi = MagicMock()
        poi.id = poi_id
        poi.latitude = -23.5510
        poi.longitude = -46.6510
        poi.quality_score = 0.8

        # First occurrence - further from road (500m)
        segment_poi1 = MagicMock()
        segment_poi1.id = uuid4()
        segment_poi1.segment_id = segment_id
        segment_poi1.poi_id = poi_id
        segment_poi1.poi = poi
        segment_poi1.search_point_index = 2
        segment_poi1.straight_line_distance_m = 500

        map_segment1 = MagicMock()
        map_segment1.segment_id = segment_id
        map_segment1.sequence_order = 0
        map_segment1.distance_from_origin_km = Decimal("0.0")

        # Second occurrence - closer to road (200m)
        segment_poi2 = MagicMock()
        segment_poi2.id = uuid4()
        segment_poi2.segment_id = segment_id
        segment_poi2.poi_id = poi_id
        segment_poi2.poi = poi
        segment_poi2.search_point_index = 5
        segment_poi2.straight_line_distance_m = 200

        map_segment2 = MagicMock()
        map_segment2.segment_id = segment_id
        map_segment2.sequence_order = 1
        map_segment2.distance_from_origin_km = Decimal("5.0")

        # Process both occurrences
        segment_pois_with_map_segments = [
            (segment_poi1, map_segment1),
            (segment_poi2, map_segment2),
        ]

        route_geometry = [(-23.5000, -46.6000), (-23.6000, -46.7000)]

        # The method should deduplicate and keep the one with shorter access
        result = await service._create_map_pois(
            map_id=uuid4(),
            segment_pois_with_map_segments=segment_pois_with_map_segments,
            route_geometry=route_geometry,
            route_total_km=20.0,
            global_sps=[],
        )

        # Should only create 1 MapPOI (the one with 200m distance)
        num_pois, poi_to_map_poi = result
        assert num_pois == 1


class TestMapSegmentCreation:
    """Tests for MapSegment creation from RouteSegments."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_creates_map_segments_in_order(self, mock_session):
        """Test that MapSegments are created with correct sequence order."""
        from api.services.map_assembly_service import MapAssemblyService

        service = MapAssemblyService(mock_session)
        service.map_segment_repo.bulk_create = AsyncMock()

        segments = [
            MagicMock(id=uuid4(), length_km=Decimal("5.0")),
            MagicMock(id=uuid4(), length_km=Decimal("8.0")),
            MagicMock(id=uuid4(), length_km=Decimal("3.0")),
        ]

        map_id = uuid4()
        result = await service._create_map_segments(map_id, segments)

        assert len(result) == 3
        assert result[0].sequence_order == 0
        assert result[1].sequence_order == 1
        assert result[2].sequence_order == 2

    @pytest.mark.asyncio
    async def test_calculates_cumulative_distance(self, mock_session):
        """Test that cumulative distance is calculated correctly."""
        from api.services.map_assembly_service import MapAssemblyService

        service = MapAssemblyService(mock_session)
        service.map_segment_repo.bulk_create = AsyncMock()

        segments = [
            MagicMock(id=uuid4(), length_km=Decimal("5.0")),
            MagicMock(id=uuid4(), length_km=Decimal("8.0")),
            MagicMock(id=uuid4(), length_km=Decimal("3.0")),
        ]

        map_id = uuid4()
        result = await service._create_map_segments(map_id, segments)

        assert result[0].distance_from_origin_km == Decimal("0.0")
        assert result[1].distance_from_origin_km == Decimal("5.0")
        assert result[2].distance_from_origin_km == Decimal("13.0")


class TestSegmentPOIAssociation:
    """Tests for associating POIs to segments."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def segment_service(self, mock_session):
        """Create SegmentService with mocked session."""
        return SegmentService(mock_session)

    @pytest.mark.asyncio
    async def test_associates_new_pois_to_segment(self, segment_service):
        """Test that new POIs are associated to segment."""
        segment = MagicMock()
        segment.id = uuid4()

        poi_id = uuid4()
        pois_with_data = [(poi_id, 0, 500)]  # (poi_id, sp_index, distance_m)

        segment_service.segment_poi_repo.exists_for_segment_poi = AsyncMock(return_value=False)
        segment_service.segment_poi_repo.bulk_create = AsyncMock()
        segment_service.segment_repo.mark_pois_fetched = AsyncMock()

        result = await segment_service.associate_pois_to_segment(segment, pois_with_data)

        assert len(result) == 1
        segment_service.segment_repo.mark_pois_fetched.assert_called_once_with(segment.id)

    @pytest.mark.asyncio
    async def test_skips_existing_poi_associations(self, segment_service):
        """Test that existing POI associations are skipped."""
        segment = MagicMock()
        segment.id = uuid4()

        poi_id = uuid4()
        pois_with_data = [(poi_id, 0, 500)]

        # POI already associated
        segment_service.segment_poi_repo.exists_for_segment_poi = AsyncMock(return_value=True)
        segment_service.segment_poi_repo.bulk_create = AsyncMock()
        segment_service.segment_repo.mark_pois_fetched = AsyncMock()

        result = await segment_service.associate_pois_to_segment(segment, pois_with_data)

        # Should not create any new associations
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_marks_segment_as_fetched(self, segment_service):
        """Test that segment is marked as POIs fetched after associating POIs."""
        segment = MagicMock()
        segment.id = uuid4()

        poi_id = uuid4()
        pois_with_data = [(poi_id, 0, 500)]  # At least one POI to trigger the mark

        segment_service.segment_poi_repo.exists_for_segment_poi = AsyncMock(return_value=False)
        segment_service.segment_poi_repo.bulk_create = AsyncMock()
        segment_service.segment_repo.mark_pois_fetched = AsyncMock()

        await segment_service.associate_pois_to_segment(segment, pois_with_data)

        segment_service.segment_repo.mark_pois_fetched.assert_called_once_with(segment.id)


class TestRouteStepExtraction:
    """Tests for RouteStep extraction from OSRM response."""

    def test_route_step_has_start_coords(self):
        """Test that RouteStep provides start coordinates."""
        step = RouteStep(
            distance_m=5000.0,
            duration_s=300.0,
            geometry=[(-23.5505, -46.6333), (-23.5700, -46.6500)],
            road_name="BR-116",
            maneuver_type="turn",
            maneuver_modifier="left",
            maneuver_location=(-23.5505, -46.6333),
        )

        assert step.start_coords == (-23.5505, -46.6333)

    def test_route_step_has_end_coords(self):
        """Test that RouteStep provides end coordinates."""
        step = RouteStep(
            distance_m=5000.0,
            duration_s=300.0,
            geometry=[(-23.5505, -46.6333), (-23.5700, -46.6500)],
            road_name="BR-116",
            maneuver_type="turn",
            maneuver_modifier="left",
            maneuver_location=(-23.5505, -46.6333),
        )

        assert step.end_coords == (-23.5700, -46.6500)

    def test_route_step_has_distance_km(self):
        """Test that RouteStep provides distance in km."""
        step = RouteStep(
            distance_m=5000.0,  # 5000 meters
            duration_s=300.0,
            geometry=[(-23.5505, -46.6333), (-23.5700, -46.6500)],
            road_name="BR-116",
            maneuver_type="turn",
            maneuver_modifier="left",
            maneuver_location=(-23.5505, -46.6333),
        )

        assert step.distance_km == 5.0  # 5000m = 5km


class TestBulkSegmentOperations:
    """Tests for bulk segment operations."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def segment_service(self, mock_session):
        """Create SegmentService with mocked session."""
        return SegmentService(mock_session)

    @pytest.fixture
    def sample_steps(self):
        """Create sample RouteSteps for bulk operations."""
        return [
            RouteStep(
                distance_m=5000.0,
                duration_s=300.0,
                geometry=[(-23.5505, -46.6333), (-23.5700, -46.6500)],
                road_name="BR-116",
                maneuver_type="turn",
                maneuver_modifier="left",
                maneuver_location=(-23.5505, -46.6333),
            ),
            RouteStep(
                distance_m=3000.0,
                duration_s=180.0,
                geometry=[(-23.5700, -46.6500), (-23.5850, -46.6620)],
                road_name="BR-116",
                maneuver_type="continue",
                maneuver_modifier=None,
                maneuver_location=(-23.5700, -46.6500),
            ),
        ]

    @pytest.mark.asyncio
    async def test_bulk_get_or_create_all_new(self, segment_service, sample_steps):
        """Test bulk creation when all segments are new."""
        segment_service.segment_repo.bulk_get_by_hashes = AsyncMock(return_value={})
        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=None)
        segment_service.segment_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        results = await segment_service.bulk_get_or_create_segments(sample_steps)

        assert len(results) == 2
        assert all(is_new for _, is_new in results)

    @pytest.mark.asyncio
    async def test_bulk_get_or_create_mixed(self, segment_service, sample_steps):
        """Test bulk operation with some existing segments."""
        existing_segment = MagicMock()
        existing_segment.id = uuid4()

        # First step has existing segment
        step1_hash = SegmentService.calculate_segment_hash(
            sample_steps[0].start_coords[0],
            sample_steps[0].start_coords[1],
            sample_steps[0].end_coords[0],
            sample_steps[0].end_coords[1],
        )

        segment_service.segment_repo.bulk_get_by_hashes = AsyncMock(
            return_value={step1_hash: existing_segment}
        )
        segment_service.segment_repo.increment_usage_count = AsyncMock()
        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=None)
        segment_service.segment_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        results = await segment_service.bulk_get_or_create_segments(sample_steps)

        assert len(results) == 2
        # First is existing
        assert results[0][1] is False
        # Second is new
        assert results[1][1] is True
