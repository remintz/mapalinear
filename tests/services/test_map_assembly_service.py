"""
Tests for MapAssemblyService.

Tests the map assembly service including:
- Creating MapSegment records
- Creating MapPOI records with junction calculation
- POI deduplication across segments
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.services.map_assembly_service import MapAssemblyService
from api.database.models.route_segment import RouteSegment
from api.database.models.map_segment import MapSegment
from api.database.models.segment_poi import SegmentPOI
from api.database.models.poi import POI


class TestMapAssemblyServiceInit:
    """Tests for MapAssemblyService initialization."""

    def test_init_creates_repositories(self):
        """Test that initialization creates required repositories."""
        mock_session = MagicMock()

        service = MapAssemblyService(mock_session)

        assert service.session == mock_session
        assert service.map_repo is not None
        assert service.map_segment_repo is not None
        assert service.map_poi_repo is not None
        assert service.poi_repo is not None
        assert service.segment_poi_repo is not None
        assert service.junction_service is not None


class TestCreateMapSegments:
    """Tests for the _create_map_segments method."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def assembly_service(self, mock_session):
        service = MapAssemblyService(mock_session)
        service.map_segment_repo.bulk_create = AsyncMock()
        return service

    @pytest.fixture
    def sample_segments(self):
        """Create sample RouteSegments."""
        return [
            MagicMock(id=uuid4(), length_km=Decimal("5.0")),
            MagicMock(id=uuid4(), length_km=Decimal("3.0")),
            MagicMock(id=uuid4(), length_km=Decimal("7.0")),
        ]

    @pytest.mark.asyncio
    async def test_creates_map_segments_for_all_route_segments(
        self, assembly_service, sample_segments
    ):
        """Test that MapSegments are created for all RouteSegments."""
        map_id = uuid4()

        result = await assembly_service._create_map_segments(map_id, sample_segments)

        assert len(result) == 3
        assembly_service.map_segment_repo.bulk_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_map_segments_have_sequential_order(
        self, assembly_service, sample_segments
    ):
        """Test that MapSegments have sequential order."""
        map_id = uuid4()

        result = await assembly_service._create_map_segments(map_id, sample_segments)

        for i, map_segment in enumerate(result):
            assert map_segment.sequence_order == i

    @pytest.mark.asyncio
    async def test_cumulative_distance_is_calculated(
        self, assembly_service, sample_segments
    ):
        """Test that cumulative distance is calculated correctly."""
        map_id = uuid4()

        result = await assembly_service._create_map_segments(map_id, sample_segments)

        # First segment starts at 0
        assert result[0].distance_from_origin_km == Decimal("0.0")
        # Second segment starts at 5km (first segment length)
        assert result[1].distance_from_origin_km == Decimal("5.0")
        # Third segment starts at 8km (5 + 3)
        assert result[2].distance_from_origin_km == Decimal("8.0")

    @pytest.mark.asyncio
    async def test_empty_segments_list(self, assembly_service):
        """Test with empty segments list."""
        map_id = uuid4()

        result = await assembly_service._create_map_segments(map_id, [])

        assert len(result) == 0


class TestCreateMapPOIs:
    """Tests for the _create_map_pois method."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def assembly_service(self, mock_session):
        service = MapAssemblyService(mock_session)
        service.map_poi_repo.bulk_create = AsyncMock()
        return service

    @pytest.fixture
    def sample_route_geometry(self):
        """Create sample route geometry."""
        return [
            (-23.5000, -46.6000),
            (-23.5500, -46.6500),
            (-23.6000, -46.7000),
        ]

    @pytest.fixture
    def sample_segment_pois_with_map_segments(self):
        """Create sample SegmentPOIs with MapSegments."""
        poi_id = uuid4()
        segment_id = uuid4()

        # Create mock POI
        poi = MagicMock()
        poi.id = poi_id
        poi.latitude = -23.5510
        poi.longitude = -46.6510
        poi.quality_score = 0.8

        # Create mock SegmentPOI
        segment_poi = MagicMock()
        segment_poi.id = uuid4()
        segment_poi.segment_id = segment_id
        segment_poi.poi_id = poi_id
        segment_poi.poi = poi
        segment_poi.search_point_index = 2
        segment_poi.straight_line_distance_m = 300

        # Create mock MapSegment
        map_segment = MagicMock()
        map_segment.segment_id = segment_id
        map_segment.sequence_order = 0
        map_segment.distance_from_origin_km = Decimal("0.0")

        return [(segment_poi, map_segment)]

    @pytest.mark.asyncio
    async def test_creates_map_pois(
        self, assembly_service, sample_segment_pois_with_map_segments, sample_route_geometry
    ):
        """Test that MapPOIs are created."""
        map_id = uuid4()
        global_sps = []

        result = await assembly_service._create_map_pois(
            map_id=map_id,
            segment_pois_with_map_segments=sample_segment_pois_with_map_segments,
            route_geometry=sample_route_geometry,
            route_total_km=20.0,
            global_sps=global_sps,
        )

        num_pois, poi_to_map_poi = result
        assert num_pois == 1
        assert isinstance(poi_to_map_poi, dict)
        assembly_service.map_poi_repo.bulk_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduplicates_pois(self, assembly_service, sample_route_geometry):
        """Test that duplicate POIs are deduplicated, keeping the one with shorter access."""
        map_id = uuid4()
        poi_id = uuid4()
        segment_id = uuid4()

        # Create mock POI
        poi = MagicMock()
        poi.id = poi_id
        poi.latitude = -23.5510
        poi.longitude = -46.6510
        poi.quality_score = 0.8

        # First occurrence - further from road
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

        # Second occurrence - closer to road (should be kept)
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

        segment_pois_with_map_segments = [
            (segment_poi1, map_segment1),
            (segment_poi2, map_segment2),
        ]

        result = await assembly_service._create_map_pois(
            map_id=map_id,
            segment_pois_with_map_segments=segment_pois_with_map_segments,
            route_geometry=sample_route_geometry,
            route_total_km=20.0,
            global_sps=[],
        )

        # Should only create 1 MapPOI (deduplicated)
        num_pois, poi_to_map_poi = result
        assert num_pois == 1

    @pytest.mark.asyncio
    async def test_skips_pois_without_poi_data(self, assembly_service, sample_route_geometry):
        """Test that SegmentPOIs without POI data are skipped."""
        map_id = uuid4()
        segment_id = uuid4()

        segment_poi = MagicMock()
        segment_poi.id = uuid4()
        segment_poi.segment_id = segment_id
        segment_poi.poi = None  # No POI data

        map_segment = MagicMock()
        map_segment.segment_id = segment_id
        map_segment.sequence_order = 0
        map_segment.distance_from_origin_km = Decimal("0.0")

        segment_pois_with_map_segments = [(segment_poi, map_segment)]

        result = await assembly_service._create_map_pois(
            map_id=map_id,
            segment_pois_with_map_segments=segment_pois_with_map_segments,
            route_geometry=sample_route_geometry,
            route_total_km=20.0,
            global_sps=[],
        )

        num_pois, poi_to_map_poi = result
        assert num_pois == 0
        assert poi_to_map_poi == {}


class TestAssembleMap:
    """Tests for the main assemble_map method."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def assembly_service(self, mock_session):
        service = MapAssemblyService(mock_session)
        service.map_segment_repo.bulk_create = AsyncMock()
        service.map_poi_repo.bulk_create = AsyncMock()
        service.segment_poi_repo.get_by_segment_with_pois = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def sample_segments(self):
        """Create sample RouteSegments."""
        return [
            MagicMock(
                id=uuid4(),
                length_km=Decimal("5.0"),
                search_points=[
                    {"lat": -23.5, "lon": -46.6, "index": 0, "distance_from_segment_start_km": 0},
                ],
            ),
        ]

    @pytest.fixture
    def sample_route_geometry(self):
        return [(-23.5, -46.6), (-23.6, -46.7)]

    @pytest.mark.asyncio
    async def test_assemble_map_returns_counts(
        self, assembly_service, sample_segments, sample_route_geometry
    ):
        """Test that assemble_map returns correct counts."""
        map_id = uuid4()

        num_segments, num_pois, poi_to_map_poi = await assembly_service.assemble_map(
            map_id=map_id,
            segments=sample_segments,
            route_geometry=sample_route_geometry,
            route_total_km=10.0,
        )

        assert num_segments == 1
        assert num_pois == 0  # No POIs in this test
        assert poi_to_map_poi == {}

    @pytest.mark.asyncio
    async def test_assemble_map_creates_map_segments(
        self, assembly_service, sample_segments, sample_route_geometry
    ):
        """Test that assemble_map creates MapSegments."""
        map_id = uuid4()

        await assembly_service.assemble_map(
            map_id=map_id,
            segments=sample_segments,
            route_geometry=sample_route_geometry,
            route_total_km=10.0,
        )

        assembly_service.map_segment_repo.bulk_create.assert_called_once()


class TestRecalculateDistances:
    """Tests for the recalculate_distances method."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def assembly_service(self, mock_session):
        return MapAssemblyService(mock_session)

    @pytest.mark.asyncio
    async def test_recalculate_distances_returns_count(self, assembly_service):
        """Test that recalculate_distances returns update count."""
        map_id = uuid4()

        # Mock empty POIs
        assembly_service.map_poi_repo.get_pois_for_map = AsyncMock(return_value=[])
        assembly_service.map_segment_repo.get_by_map = AsyncMock(return_value=[])

        result = await assembly_service.recalculate_distances(map_id)

        assert result == 0


class TestOrderPoisByDistance:
    """Tests for the order_pois_by_distance method."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        return session

    @pytest.fixture
    def assembly_service(self, mock_session):
        return MapAssemblyService(mock_session)

    @pytest.mark.asyncio
    async def test_order_pois_by_distance_calls_repo(self, assembly_service):
        """Test that order_pois_by_distance delegates to repository."""
        map_id = uuid4()
        expected_pois = [MagicMock(), MagicMock()]

        assembly_service.map_poi_repo.get_pois_for_map = AsyncMock(
            return_value=expected_pois
        )

        result = await assembly_service.order_pois_by_distance(map_id)

        assert result == expected_pois
        assembly_service.map_poi_repo.get_pois_for_map.assert_called_once_with(
            map_id, include_poi_details=True
        )


class TestGetMapStatistics:
    """Tests for the get_map_statistics method."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        return session

    @pytest.fixture
    def assembly_service(self, mock_session):
        return MapAssemblyService(mock_session)

    @pytest.mark.asyncio
    async def test_get_map_statistics_returns_dict(self, assembly_service):
        """Test that get_map_statistics returns statistics dict."""
        map_id = uuid4()

        assembly_service.map_segment_repo.count_by_map = AsyncMock(return_value=5)
        assembly_service.map_segment_repo.get_total_distance_for_map = AsyncMock(
            return_value=50.0
        )
        assembly_service.map_poi_repo.get_pois_for_map = AsyncMock(return_value=[])

        result = await assembly_service.get_map_statistics(map_id)

        assert "num_segments" in result
        assert "total_distance_km" in result
        assert "num_pois" in result
        assert "pois_by_type" in result
        assert "pois_by_side" in result

    @pytest.mark.asyncio
    async def test_get_map_statistics_counts_pois_by_type(self, assembly_service):
        """Test that statistics counts POIs by type."""
        map_id = uuid4()

        # Create mock POIs with different types
        poi1 = MagicMock()
        poi1.poi = MagicMock()
        poi1.poi.type = "gas_station"
        poi1.side = "left"

        poi2 = MagicMock()
        poi2.poi = MagicMock()
        poi2.poi.type = "restaurant"
        poi2.side = "right"

        poi3 = MagicMock()
        poi3.poi = MagicMock()
        poi3.poi.type = "gas_station"
        poi3.side = "left"

        assembly_service.map_segment_repo.count_by_map = AsyncMock(return_value=1)
        assembly_service.map_segment_repo.get_total_distance_for_map = AsyncMock(
            return_value=10.0
        )
        assembly_service.map_poi_repo.get_pois_for_map = AsyncMock(
            return_value=[poi1, poi2, poi3]
        )

        result = await assembly_service.get_map_statistics(map_id)

        assert result["num_pois"] == 3
        assert result["pois_by_type"]["gas_station"] == 2
        assert result["pois_by_type"]["restaurant"] == 1
        assert result["pois_by_side"]["left"] == 2
        assert result["pois_by_side"]["right"] == 1
