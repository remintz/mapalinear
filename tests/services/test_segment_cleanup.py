"""
Tests for segment cleanup and orphan management.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.database.models.route_segment import RouteSegment
from api.database.models.map_segment import MapSegment
from api.database.repositories.route_segment import RouteSegmentRepository
from api.services.database_maintenance_service import (
    DatabaseMaintenanceService,
    MaintenanceStats,
    DatabaseStats,
)


class TestRouteSegmentRepositoryUsageCount:
    """Tests for usage count operations in RouteSegmentRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create a RouteSegmentRepository with mock session."""
        return RouteSegmentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_decrement_usage_count(self, repo, mock_session):
        """Test that decrement_usage_count calls execute with correct query."""
        segment_id = uuid4()

        await repo.decrement_usage_count(segment_id)

        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_decrement_usage_empty_list(self, repo, mock_session):
        """Test that bulk_decrement_usage does nothing with empty list."""
        await repo.bulk_decrement_usage([])

        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_decrement_usage(self, repo, mock_session):
        """Test that bulk_decrement_usage calls execute with correct query."""
        segment_ids = [uuid4(), uuid4(), uuid4()]

        await repo.bulk_decrement_usage(segment_ids)

        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()


class TestRouteSegmentRepositoryOrphanDetection:
    """Tests for orphan segment detection in RouteSegmentRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create a RouteSegmentRepository with mock session."""
        return RouteSegmentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_find_orphan_segment_ids_returns_list(self, repo, mock_session):
        """Test that find_orphan_segment_ids returns a list of UUIDs."""
        orphan_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [orphan_id]
        mock_session.execute.return_value = mock_result

        result = await repo.find_orphan_segment_ids()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == orphan_id

    @pytest.mark.asyncio
    async def test_count_orphan_segments(self, repo, mock_session):
        """Test that count_orphan_segments returns correct count."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await repo.count_orphan_segments()

        assert result == 5

    @pytest.mark.asyncio
    async def test_delete_orphan_segments_no_orphans(self, repo, mock_session):
        """Test that delete_orphan_segments returns 0 when no orphans."""
        # Mock find_orphan_segment_ids to return empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.delete_orphan_segments()

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_statistics_includes_orphan_count(self, repo, mock_session):
        """Test that get_statistics includes orphan_segments count."""
        # Mock multiple execute calls for different stats
        mock_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar=lambda: 10),  # total
            MagicMock(scalar=lambda: 8),   # with_pois
            MagicMock(scalar=lambda: 25),  # total_usage
            MagicMock(scalar=lambda: 100.0),  # total_length
            MagicMock(scalar=lambda: 2),   # orphan count
        ])

        result = await repo.get_statistics()

        assert "orphan_segments" in result
        assert result["total_segments"] == 10
        assert result["orphan_segments"] == 2


class TestDatabaseMaintenanceServiceSegments:
    """Tests for segment maintenance in DatabaseMaintenanceService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a DatabaseMaintenanceService with mock session."""
        return DatabaseMaintenanceService(mock_session)

    @pytest.mark.asyncio
    async def test_count_segments_returns_tuple(self, service, mock_session):
        """Test that _count_segments returns (total, orphan) tuple."""
        mock_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar=lambda: 10),  # total
            MagicMock(scalar=lambda: 3),   # orphan
        ])

        total, orphan = await service._count_segments()

        assert total == 10
        assert orphan == 3

    @pytest.mark.asyncio
    async def test_count_segments_handles_error(self, service, mock_session):
        """Test that _count_segments returns (0, 0) on error."""
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

        total, orphan = await service._count_segments()

        assert total == 0
        assert orphan == 0

    @pytest.mark.asyncio
    async def test_find_orphan_segment_ids_returns_strings(self, service, mock_session):
        """Test that find_orphan_segment_ids returns list of string UUIDs."""
        orphan_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [orphan_id]
        mock_session.execute.return_value = mock_result

        result = await service.find_orphan_segment_ids()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == str(orphan_id)

    @pytest.mark.asyncio
    async def test_find_orphan_segment_ids_handles_error(self, service, mock_session):
        """Test that find_orphan_segment_ids returns [] on error."""
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

        result = await service.find_orphan_segment_ids()

        assert result == []

    @pytest.mark.asyncio
    async def test_delete_orphan_segments_dry_run(self, service, mock_session):
        """Test that delete_orphan_segments dry_run doesn't delete."""
        orphan_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [orphan_id]
        mock_session.execute.return_value = mock_result

        result = await service.delete_orphan_segments(dry_run=True)

        assert result == 1
        # Should only have called execute once (for finding orphans)
        # Not for actual deletion
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_orphan_segments_no_orphans(self, service, mock_session):
        """Test that delete_orphan_segments returns 0 when no orphans."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await service.delete_orphan_segments(dry_run=False)

        assert result == 0

    @pytest.mark.asyncio
    async def test_run_full_maintenance_includes_segments(self, service, mock_session):
        """Test that run_full_maintenance processes segments."""
        # Mock all the various calls
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: []),
            scalar=lambda: 0,
            rowcount=0,
        ))

        stats = await service.run_full_maintenance(dry_run=True)

        assert isinstance(stats, MaintenanceStats)
        assert hasattr(stats, 'orphan_segments_found')
        assert hasattr(stats, 'orphan_segments_deleted')


class TestMapStorageServiceDeleteSegmentUsage:
    """Tests for segment usage tracking during map deletion."""

    @pytest.mark.asyncio
    async def test_delete_map_decrements_usage_count(self):
        """Test that deleting a map decrements segment usage counts."""
        from api.services.map_storage_service_db import MapStorageServiceDB

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        service = MapStorageServiceDB(mock_session)

        # Mock the repositories
        segment_ids = [uuid4(), uuid4()]
        service._map_segment_repo = MagicMock()
        service._map_segment_repo.get_segment_ids_for_map = AsyncMock(
            return_value=segment_ids
        )

        service._route_segment_repo = MagicMock()
        service._route_segment_repo.bulk_decrement_usage = AsyncMock()

        service.map_repo = MagicMock()
        service.map_repo.delete_by_id = AsyncMock(return_value=True)

        map_id = str(uuid4())
        result = await service.delete_map_permanently(map_id)

        assert result is True
        service._route_segment_repo.bulk_decrement_usage.assert_called_once_with(
            segment_ids
        )

    @pytest.mark.asyncio
    async def test_delete_map_no_segments(self):
        """Test that deleting a map without segments still works."""
        from api.services.map_storage_service_db import MapStorageServiceDB

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        service = MapStorageServiceDB(mock_session)

        # Mock the repositories - no segments
        service._map_segment_repo = MagicMock()
        service._map_segment_repo.get_segment_ids_for_map = AsyncMock(
            return_value=[]
        )

        service._route_segment_repo = MagicMock()
        service._route_segment_repo.bulk_decrement_usage = AsyncMock()

        service.map_repo = MagicMock()
        service.map_repo.delete_by_id = AsyncMock(return_value=True)

        map_id = str(uuid4())
        result = await service.delete_map_permanently(map_id)

        assert result is True
        # Should not call decrement since no segments
        service._route_segment_repo.bulk_decrement_usage.assert_not_called()
