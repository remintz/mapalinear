"""
Tests for SegmentService.

Tests the segment management service including:
- Segment hash calculation
- Search point generation
- Segment creation and reuse
- POI association with segments
"""

import hashlib
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.services.segment_service import SegmentService
from api.providers.models import RouteStep


class TestCalculateSegmentHash:
    """Tests for the calculate_segment_hash static method."""

    def test_basic_hash_calculation(self):
        """Test that hash is calculated correctly."""
        hash_value = SegmentService.calculate_segment_hash(
            start_lat=-23.5505,
            start_lon=-46.6333,
            end_lat=-23.5605,
            end_lon=-46.6433,
        )

        # Hash should be 32 character hex string (MD5)
        assert len(hash_value) == 32
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_hash_uses_4_decimal_precision(self):
        """Test that coordinates are rounded to 4 decimals."""
        # These should produce the same hash when rounded to 4 decimals
        # -23.55050001 rounds to -23.5505
        # -23.55050009 rounds to -23.5505
        hash1 = SegmentService.calculate_segment_hash(
            start_lat=-23.55050001,
            start_lon=-46.63330001,
            end_lat=-23.56050001,
            end_lon=-46.64330001,
        )
        hash2 = SegmentService.calculate_segment_hash(
            start_lat=-23.55050009,
            start_lon=-46.63330009,
            end_lat=-23.56050009,
            end_lon=-46.64330009,
        )

        assert hash1 == hash2

    def test_different_coordinates_produce_different_hashes(self):
        """Test that different coordinates produce different hashes."""
        hash1 = SegmentService.calculate_segment_hash(
            start_lat=-23.5505,
            start_lon=-46.6333,
            end_lat=-23.5605,
            end_lon=-46.6433,
        )
        hash2 = SegmentService.calculate_segment_hash(
            start_lat=-23.5506,  # Different start lat
            start_lon=-46.6333,
            end_lat=-23.5605,
            end_lon=-46.6433,
        )

        assert hash1 != hash2

    def test_hash_is_deterministic(self):
        """Test that same coordinates always produce same hash."""
        coords = {
            "start_lat": -23.5505,
            "start_lon": -46.6333,
            "end_lat": -23.5605,
            "end_lon": -46.6433,
        }

        hash1 = SegmentService.calculate_segment_hash(**coords)
        hash2 = SegmentService.calculate_segment_hash(**coords)
        hash3 = SegmentService.calculate_segment_hash(**coords)

        assert hash1 == hash2 == hash3

    def test_hash_format_matches_expected(self):
        """Test that hash format matches expected MD5 format."""
        hash_value = SegmentService.calculate_segment_hash(
            start_lat=-23.5505,
            start_lon=-46.6333,
            end_lat=-23.5605,
            end_lon=-46.6433,
        )

        # Manually calculate expected hash
        coords_str = "-23.5505,-46.6333|-23.5605,-46.6433"
        expected_hash = hashlib.md5(coords_str.encode()).hexdigest()

        assert hash_value == expected_hash

    def test_hash_with_version_suffix(self):
        """Test that version suffix creates different hash."""
        coords = {
            "start_lat": -23.5505,
            "start_lon": -46.6333,
            "end_lat": -23.5605,
            "end_lon": -46.6433,
        }

        hash_without_version = SegmentService.calculate_segment_hash(**coords)
        hash_with_version = SegmentService.calculate_segment_hash(
            **coords, version_suffix="20260108120000123456"
        )

        # Hashes should be different
        assert hash_without_version != hash_with_version
        # Both should be valid MD5 hashes
        assert len(hash_without_version) == 32
        assert len(hash_with_version) == 32

    def test_hash_with_different_version_suffixes(self):
        """Test that different version suffixes produce different hashes."""
        coords = {
            "start_lat": -23.5505,
            "start_lon": -46.6333,
            "end_lat": -23.5605,
            "end_lon": -46.6433,
        }

        hash_v1 = SegmentService.calculate_segment_hash(
            **coords, version_suffix="v1"
        )
        hash_v2 = SegmentService.calculate_segment_hash(
            **coords, version_suffix="v2"
        )

        assert hash_v1 != hash_v2

    def test_hash_with_version_suffix_format(self):
        """Test that hash with version suffix matches expected format."""
        hash_value = SegmentService.calculate_segment_hash(
            start_lat=-23.5505,
            start_lon=-46.6333,
            end_lat=-23.5605,
            end_lon=-46.6433,
            version_suffix="test_version",
        )

        # Manually calculate expected hash
        coords_str = "-23.5505,-46.6333|-23.5605,-46.6433|test_version"
        expected_hash = hashlib.md5(coords_str.encode()).hexdigest()

        assert hash_value == expected_hash


class TestGenerateSearchPoints:
    """Tests for the generate_search_points static method."""

    def test_short_segment_returns_empty_list(self):
        """Test that segments shorter than 1km return no search points."""
        geometry = [(-23.5505, -46.6333), (-23.5510, -46.6338)]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=0.5,  # Less than 1km
        )

        assert search_points == []

    def test_minimum_length_segment(self):
        """Test that segments at exactly 1km get search points."""
        # Create a geometry approximately 1km long
        geometry = [
            (-23.5505, -46.6333),
            (-23.5550, -46.6380),
            (-23.5595, -46.6423),
        ]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=1.0,
        )

        # Should have at least 1 search point
        assert len(search_points) >= 1

    def test_search_point_structure(self):
        """Test that search points have correct structure."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.5700, -46.6500),
        ]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=5.0,
        )

        assert len(search_points) > 0

        for sp in search_points:
            assert "index" in sp
            assert "lat" in sp
            assert "lon" in sp
            assert "distance_from_segment_start_km" in sp

            # Check types
            assert isinstance(sp["index"], int)
            assert isinstance(sp["lat"], float)
            assert isinstance(sp["lon"], float)
            assert isinstance(sp["distance_from_segment_start_km"], float)

    def test_search_points_interval(self):
        """Test that search points are generated every ~1km."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.6005, -46.6833),
        ]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=10.0,
        )

        # Should have approximately 11 search points (0km, 1km, 2km, ..., 10km)
        assert len(search_points) >= 10
        assert len(search_points) <= 12

    def test_search_points_are_sequential(self):
        """Test that search point indices are sequential."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.6005, -46.6833),
        ]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=5.0,
        )

        for i, sp in enumerate(search_points):
            assert sp["index"] == i

    def test_search_points_distances_increase(self):
        """Test that distances from start increase monotonically."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.6005, -46.6833),
        ]

        search_points = SegmentService.generate_search_points(
            geometry=geometry,
            length_km=5.0,
        )

        distances = [sp["distance_from_segment_start_km"] for sp in search_points]

        for i in range(1, len(distances)):
            assert distances[i] > distances[i - 1]

    def test_empty_geometry_returns_empty_list(self):
        """Test that empty geometry returns no search points."""
        search_points = SegmentService.generate_search_points(
            geometry=[],
            length_km=5.0,
        )

        assert search_points == []

    def test_single_point_geometry_returns_empty_list(self):
        """Test that single point geometry returns no search points."""
        search_points = SegmentService.generate_search_points(
            geometry=[(-23.5505, -46.6333)],
            length_km=5.0,
        )

        assert search_points == []


class TestInterpolatePointAtDistance:
    """Tests for the _interpolate_point_at_distance static method."""

    def test_zero_distance_returns_first_point(self):
        """Test that zero distance returns the first geometry point."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.5600, -46.6400),
            (-23.5700, -46.6500),
        ]
        cumulative_distances = [0.0, 1.0, 2.0]

        result = SegmentService._interpolate_point_at_distance(
            geometry, cumulative_distances, 0.0
        )

        assert result == (-23.5505, -46.6333)

    def test_max_distance_returns_last_point(self):
        """Test that max distance returns the last geometry point."""
        geometry = [
            (-23.5505, -46.6333),
            (-23.5600, -46.6400),
            (-23.5700, -46.6500),
        ]
        cumulative_distances = [0.0, 1.0, 2.0]

        result = SegmentService._interpolate_point_at_distance(
            geometry, cumulative_distances, 2.5
        )

        assert result == (-23.5700, -46.6500)

    def test_midpoint_interpolation(self):
        """Test interpolation at midpoint of a segment."""
        geometry = [
            (-23.5000, -46.6000),
            (-23.6000, -46.7000),
        ]
        cumulative_distances = [0.0, 10.0]

        result = SegmentService._interpolate_point_at_distance(
            geometry, cumulative_distances, 5.0
        )

        # Should be approximately at the midpoint
        assert abs(result[0] - (-23.5500)) < 0.001
        assert abs(result[1] - (-46.6500)) < 0.001


class TestSegmentServiceAsync:
    """Tests for async methods of SegmentService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def segment_service(self, mock_session):
        """Create a SegmentService with mocked session."""
        return SegmentService(mock_session)

    @pytest.fixture
    def sample_route_step(self):
        """Create a sample RouteStep for testing."""
        return RouteStep(
            distance_m=5000.0,
            duration_s=300.0,
            geometry=[
                (-23.5505, -46.6333),
                (-23.5600, -46.6400),
                (-23.5700, -46.6500),
            ],
            road_name="BR-101",
            maneuver_type="turn",
            maneuver_modifier="left",
            maneuver_location=(-23.5505, -46.6333),
        )

    @pytest.mark.asyncio
    async def test_get_or_create_segment_creates_new(
        self, segment_service, sample_route_step, mock_session
    ):
        """Test that get_or_create_segment creates a new segment when none exists."""
        # Mock repository to return None (no existing segment)
        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=None)
        segment_service.segment_repo.create = AsyncMock(return_value=MagicMock())

        segment, is_new = await segment_service.get_or_create_segment(sample_route_step)

        assert is_new is True
        segment_service.segment_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_segment_returns_existing(
        self, segment_service, sample_route_step
    ):
        """Test that get_or_create_segment returns existing segment when found."""
        existing_segment = MagicMock()
        existing_segment.id = uuid4()

        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=existing_segment)
        segment_service.segment_repo.increment_usage_count = AsyncMock()

        segment, is_new = await segment_service.get_or_create_segment(sample_route_step)

        assert is_new is False
        assert segment == existing_segment
        segment_service.segment_repo.increment_usage_count.assert_called_once_with(
            existing_segment.id
        )

    @pytest.mark.asyncio
    async def test_needs_poi_search_returns_true_for_new_segment(self, segment_service):
        """Test that needs_poi_search returns True for segment without POIs."""
        segment = MagicMock()
        segment.pois_fetched_at = None
        segment.length_km = Decimal("5.0")

        result = await segment_service.needs_poi_search(segment)

        assert result is True

    @pytest.mark.asyncio
    async def test_needs_poi_search_returns_false_for_fetched_segment(self, segment_service):
        """Test that needs_poi_search returns False when POIs already fetched."""
        from datetime import datetime

        segment = MagicMock()
        segment.pois_fetched_at = datetime.now()
        segment.length_km = Decimal("5.0")

        result = await segment_service.needs_poi_search(segment)

        assert result is False

    @pytest.mark.asyncio
    async def test_needs_poi_search_returns_false_for_short_segment(self, segment_service):
        """Test that needs_poi_search returns False for segments < 1km."""
        segment = MagicMock()
        segment.pois_fetched_at = None
        segment.length_km = Decimal("0.5")

        result = await segment_service.needs_poi_search(segment)

        assert result is False

    @pytest.mark.asyncio
    async def test_associate_pois_to_segment(self, segment_service):
        """Test associating POIs to a segment."""
        segment = MagicMock()
        segment.id = uuid4()

        poi_id = uuid4()
        pois_with_discovery_data = [
            (poi_id, 0, 500),  # (poi_id, search_point_index, distance_m)
        ]

        segment_service.segment_poi_repo.exists_for_segment_poi = AsyncMock(return_value=False)
        segment_service.segment_poi_repo.bulk_create = AsyncMock()
        segment_service.segment_repo.mark_pois_fetched = AsyncMock()

        result = await segment_service.associate_pois_to_segment(
            segment, pois_with_discovery_data
        )

        assert len(result) == 1
        segment_service.segment_repo.mark_pois_fetched.assert_called_once_with(segment.id)

    @pytest.mark.asyncio
    async def test_associate_pois_skips_existing(self, segment_service):
        """Test that existing POI associations are skipped."""
        segment = MagicMock()
        segment.id = uuid4()

        poi_id = uuid4()
        pois_with_discovery_data = [
            (poi_id, 0, 500),
        ]

        # Mock that this association already exists
        segment_service.segment_poi_repo.exists_for_segment_poi = AsyncMock(return_value=True)
        segment_service.segment_poi_repo.bulk_create = AsyncMock()
        segment_service.segment_repo.mark_pois_fetched = AsyncMock()

        result = await segment_service.associate_pois_to_segment(
            segment, pois_with_discovery_data
        )

        # Should not create any new associations
        assert len(result) == 0


class TestBulkGetOrCreateSegments:
    """Tests for bulk_get_or_create_segments method."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def segment_service(self, mock_session):
        return SegmentService(mock_session)

    @pytest.fixture
    def sample_steps(self):
        """Create sample RouteSteps for bulk testing."""
        return [
            RouteStep(
                distance_m=5000.0,
                duration_s=300.0,
                geometry=[(-23.5505, -46.6333), (-23.5700, -46.6500)],
                road_name="BR-101",
                maneuver_type="turn",
                maneuver_modifier="left",
                maneuver_location=(-23.5505, -46.6333),
            ),
            RouteStep(
                distance_m=3000.0,
                duration_s=180.0,
                geometry=[(-23.5700, -46.6500), (-23.5850, -46.6620)],
                road_name="BR-101",
                maneuver_type="continue",
                maneuver_modifier=None,
                maneuver_location=(-23.5700, -46.6500),
            ),
        ]

    @pytest.mark.asyncio
    async def test_bulk_creates_all_new_segments(self, segment_service, sample_steps):
        """Test bulk creation when no segments exist."""
        segment_service.segment_repo.bulk_get_by_hashes = AsyncMock(return_value={})
        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=None)
        segment_service.segment_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        results = await segment_service.bulk_get_or_create_segments(sample_steps)

        assert len(results) == 2
        assert all(is_new for _, is_new in results)

    @pytest.mark.asyncio
    async def test_bulk_returns_existing_segments(self, segment_service, sample_steps):
        """Test bulk returns existing segments when they exist."""
        existing_segment = MagicMock()
        existing_segment.id = uuid4()

        # Calculate hash for first step
        step = sample_steps[0]
        hash1 = SegmentService.calculate_segment_hash(
            step.start_coords[0], step.start_coords[1],
            step.end_coords[0], step.end_coords[1]
        )

        segment_service.segment_repo.bulk_get_by_hashes = AsyncMock(
            return_value={hash1: existing_segment}
        )
        segment_service.segment_repo.increment_usage_count = AsyncMock()
        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=None)
        segment_service.segment_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        results = await segment_service.bulk_get_or_create_segments(sample_steps)

        assert len(results) == 2
        # First should be existing (is_new=False)
        assert results[0][1] is False
        # Second should be new (is_new=True)
        assert results[1][1] is True

    @pytest.mark.asyncio
    async def test_bulk_force_new_creates_all_new_segments(
        self, segment_service, sample_steps
    ):
        """Test that force_new=True creates all new segments, even if they exist."""
        existing_segment = MagicMock()
        existing_segment.id = uuid4()

        # Calculate hash for first step (without version suffix)
        step = sample_steps[0]
        hash1 = SegmentService.calculate_segment_hash(
            step.start_coords[0], step.start_coords[1],
            step.end_coords[0], step.end_coords[1]
        )

        # Existing segment would be found if we were doing normal lookup
        segment_service.segment_repo.bulk_get_by_hashes = AsyncMock(
            return_value={hash1: existing_segment}
        )
        segment_service.segment_repo.create = AsyncMock(
            side_effect=lambda s: s  # Return the segment passed in
        )

        results = await segment_service.bulk_get_or_create_segments(
            sample_steps, force_new=True
        )

        assert len(results) == 2
        # ALL segments should be new when force_new=True
        assert all(is_new for _, is_new in results)
        # bulk_get_by_hashes should NOT be called when force_new=True
        segment_service.segment_repo.bulk_get_by_hashes.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_force_new_generates_unique_hashes(
        self, segment_service, sample_steps
    ):
        """Test that force_new=True generates unique versioned hashes."""
        created_segments = []

        async def capture_create(segment):
            created_segments.append(segment)
            return segment

        segment_service.segment_repo.bulk_get_by_hashes = AsyncMock(return_value={})
        segment_service.segment_repo.get_by_hash = AsyncMock(return_value=None)
        segment_service.segment_repo.create = AsyncMock(side_effect=capture_create)

        # First call without force_new
        await segment_service.bulk_get_or_create_segments(sample_steps, force_new=False)
        hashes_without_version = [s.segment_hash for s in created_segments]
        created_segments.clear()

        # Second call with force_new - should generate different hashes
        await segment_service.bulk_get_or_create_segments(sample_steps, force_new=True)
        hashes_with_version = [s.segment_hash for s in created_segments]

        # Hashes should be different due to version suffix
        for h1, h2 in zip(hashes_without_version, hashes_with_version):
            assert h1 != h2

    @pytest.mark.asyncio
    async def test_bulk_force_new_skips_lookup(self, segment_service, sample_steps):
        """Test that force_new=True skips the database lookup entirely."""
        segment_service.segment_repo.bulk_get_by_hashes = AsyncMock(return_value={})
        segment_service.segment_repo.create = AsyncMock(
            side_effect=lambda s: s
        )

        await segment_service.bulk_get_or_create_segments(
            sample_steps, force_new=True
        )

        # Should NOT call bulk_get_by_hashes when force_new=True
        segment_service.segment_repo.bulk_get_by_hashes.assert_not_called()
        # Should still create segments
        assert segment_service.segment_repo.create.call_count == 2
