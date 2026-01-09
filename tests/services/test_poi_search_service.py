"""
Unit tests for api/services/poi_search_service.py

Tests for POI search algorithm:
- search_pois_for_segment
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from api.providers.models import GeoLocation, POI, POICategory
from api.services.poi_search_service import POISearchService


class TestSearchPoisForSegment:
    """Tests for search_pois_for_segment method."""

    @pytest.fixture
    def mock_geo_provider(self):
        """Create mock geo provider."""
        return MagicMock()

    @pytest.fixture
    def mock_poi_provider(self):
        """Create mock POI provider."""
        provider = MagicMock()
        provider.search_pois = AsyncMock()
        return provider

    @pytest.fixture
    def mock_segment(self):
        """Create mock segment with search points."""
        segment = MagicMock()
        segment.id = "test_segment_1"
        segment.search_points = [
            {"index": 0, "lat": -23.55, "lon": -46.63},
            {"index": 1, "lat": -23.56, "lon": -46.64},
        ]
        return segment

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_segment_without_search_points(
        self, mock_geo_provider, mock_poi_provider
    ):
        """Should return empty list if segment has no search points."""
        segment = MagicMock()
        segment.id = "no_search_points"
        segment.search_points = None

        service = POISearchService(mock_geo_provider, mock_poi_provider)
        result = await service.search_pois_for_segment(
            segment, [POICategory.GAS_STATION]
        )

        assert result == []
        mock_poi_provider.search_pois.assert_not_called()

    @pytest.mark.asyncio
    async def test_finds_pois_at_search_points(
        self, mock_geo_provider, mock_poi_provider, mock_segment
    ):
        """Should find POIs at each search point."""
        mock_poi_provider.search_pois.return_value = [
            POI(
                id="poi_1",
                name="Posto Shell",
                category=POICategory.GAS_STATION,
                location=GeoLocation(latitude=-23.551, longitude=-46.631),
                provider_data={},
            )
        ]

        service = POISearchService(mock_geo_provider, mock_poi_provider)
        result = await service.search_pois_for_segment(
            mock_segment, [POICategory.GAS_STATION]
        )

        assert len(result) == 1
        poi, sp_index, distance_m = result[0]
        assert poi.id == "poi_1"
        assert sp_index in [0, 1]  # Discovered at one of the search points

    @pytest.mark.asyncio
    async def test_deduplicates_pois_keeping_closest(
        self, mock_geo_provider, mock_poi_provider, mock_segment
    ):
        """Should keep only the closest discovery for each POI."""
        # Same POI found at both search points
        mock_poi_provider.search_pois.side_effect = [
            [
                POI(
                    id="poi_1",
                    name="Posto Shell",
                    category=POICategory.GAS_STATION,
                    location=GeoLocation(latitude=-23.551, longitude=-46.631),
                    provider_data={},
                )
            ],
            [
                POI(
                    id="poi_1",
                    name="Posto Shell",
                    category=POICategory.GAS_STATION,
                    location=GeoLocation(latitude=-23.551, longitude=-46.631),
                    provider_data={},
                )
            ],
        ]

        service = POISearchService(mock_geo_provider, mock_poi_provider)
        result = await service.search_pois_for_segment(
            mock_segment, [POICategory.GAS_STATION]
        )

        # Should have only one entry for poi_1
        assert len(result) == 1
        poi, sp_index, distance_m = result[0]
        assert poi.id == "poi_1"

    @pytest.mark.asyncio
    async def test_skips_abandoned_pois(
        self, mock_geo_provider, mock_poi_provider, mock_segment
    ):
        """Should skip POIs marked as abandoned."""
        mock_poi_provider.search_pois.return_value = [
            POI(
                id="abandoned_poi",
                name="Old Gas Station",
                category=POICategory.GAS_STATION,
                location=GeoLocation(latitude=-23.551, longitude=-46.631),
                provider_data={"is_abandoned": True},
            ),
            POI(
                id="active_poi",
                name="New Gas Station",
                category=POICategory.GAS_STATION,
                location=GeoLocation(latitude=-23.552, longitude=-46.632),
                provider_data={},
            ),
        ]

        service = POISearchService(mock_geo_provider, mock_poi_provider)
        result = await service.search_pois_for_segment(
            mock_segment, [POICategory.GAS_STATION]
        )

        # Should only include the active POI
        poi_ids = [poi.id for poi, _, _ in result]
        assert "abandoned_poi" not in poi_ids
        assert "active_poi" in poi_ids

    @pytest.mark.asyncio
    async def test_handles_search_errors_gracefully(
        self, mock_geo_provider, mock_poi_provider, mock_segment
    ):
        """Should continue with other search points if one fails."""
        mock_poi_provider.search_pois.side_effect = [
            Exception("API error"),  # First search point fails
            [
                POI(
                    id="poi_1",
                    name="Posto Shell",
                    category=POICategory.GAS_STATION,
                    location=GeoLocation(latitude=-23.561, longitude=-46.641),
                    provider_data={},
                )
            ],  # Second succeeds
        ]

        service = POISearchService(mock_geo_provider, mock_poi_provider)
        result = await service.search_pois_for_segment(
            mock_segment, [POICategory.GAS_STATION]
        )

        # Should still find POI from second search point
        assert len(result) == 1
        poi, _, _ = result[0]
        assert poi.id == "poi_1"
