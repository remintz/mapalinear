"""
Tests for HERE Enrichment Service - TDD Implementation.

This module contains comprehensive tests for the HERE enrichment service,
which enriches OSM POIs with additional data from HERE Maps.
"""

import pytest
import math
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

from api.services.here_enrichment_service import (
    HereEnrichmentService,
    HereEnrichmentResult,
    ENRICHABLE_TYPES,
    TYPE_TO_CATEGORY,
)
from api.providers.models import GeoLocation, POI, POICategory


class MockDBPoi:
    """Mock database POI for testing."""

    def __init__(
        self,
        id: str = "test-poi-1",
        name: str = "Test POI",
        latitude: float = -23.5505,
        longitude: float = -46.6333,
        poi_type: str = "gas_station",
        osm_id: str = "node/123456",
        here_id: str = None,
        enriched_by: List[str] = None,
    ):
        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.type = poi_type
        self.osm_id = osm_id
        self.here_id = here_id
        self._enriched_by = enriched_by or []

    def is_enriched_by(self, source: str) -> bool:
        return source in self._enriched_by


class TestHereEnrichmentServiceBasics:
    """Test basic functionality of HERE Enrichment Service."""

    def test_service_initialization(self):
        """It should initialize correctly without session."""
        service = HereEnrichmentService()
        assert service.session is None
        assert service.poi_repo is None

    def test_service_initialization_with_session(self):
        """It should initialize with database session."""
        mock_session = Mock()
        service = HereEnrichmentService(session=mock_session)
        assert service.session is mock_session
        assert service.poi_repo is not None

    def test_is_enabled_with_api_key(self):
        """It should be enabled when HERE API key is present."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            service = HereEnrichmentService()
            assert service.is_enabled() is True

    def test_is_enabled_without_api_key(self):
        """It should be disabled when HERE API key is not present."""
        from api.providers.settings import ProviderSettings

        # Create a mock service with no API key
        service = HereEnrichmentService()
        # Manually override settings to simulate no API key
        original_key = service.settings.here_api_key
        service.settings.here_api_key = None
        assert service.is_enabled() is False
        # Restore
        service.settings.here_api_key = original_key


class TestEnrichableTypes:
    """Test enrichable POI types configuration."""

    def test_gas_station_is_enrichable(self):
        """GAS_STATION should be enrichable."""
        assert "gas_station" in ENRICHABLE_TYPES

    def test_restaurant_is_enrichable(self):
        """RESTAURANT should be enrichable."""
        assert "restaurant" in ENRICHABLE_TYPES

    def test_hotel_is_enrichable(self):
        """HOTEL should be enrichable."""
        assert "hotel" in ENRICHABLE_TYPES

    def test_hospital_is_enrichable(self):
        """HOSPITAL should be enrichable."""
        assert "hospital" in ENRICHABLE_TYPES

    def test_pharmacy_is_enrichable(self):
        """PHARMACY should be enrichable."""
        assert "pharmacy" in ENRICHABLE_TYPES


class TestTypeToCategoryMapping:
    """Test mapping from POI types to POICategory enum."""

    def test_gas_station_mapping(self):
        """It should map gas_station to POICategory.GAS_STATION."""
        assert TYPE_TO_CATEGORY["gas_station"] == POICategory.GAS_STATION

    def test_restaurant_mapping(self):
        """It should map restaurant to POICategory.RESTAURANT."""
        assert TYPE_TO_CATEGORY["restaurant"] == POICategory.RESTAURANT

    def test_hotel_mapping(self):
        """It should map hotel to POICategory.HOTEL."""
        assert TYPE_TO_CATEGORY["hotel"] == POICategory.HOTEL


class TestShouldEnrich:
    """Test should_enrich logic."""

    def test_should_enrich_valid_type_not_enriched(self):
        """It should return True for enrichable type not yet enriched."""
        service = HereEnrichmentService()
        poi = MockDBPoi(poi_type="gas_station", enriched_by=[])
        assert service.should_enrich(poi) is True

    def test_should_not_enrich_already_enriched(self):
        """It should return False for already enriched POI."""
        service = HereEnrichmentService()
        poi = MockDBPoi(poi_type="gas_station", enriched_by=["here_maps"])
        assert service.should_enrich(poi) is False

    def test_should_not_enrich_invalid_type(self):
        """It should return False for non-enrichable POI type."""
        service = HereEnrichmentService()
        poi = MockDBPoi(poi_type="unknown_type", enriched_by=[])
        assert service.should_enrich(poi) is False


class TestDistanceCalculation:
    """Test distance calculation using Haversine formula."""

    def test_calculate_distance_same_point(self):
        """It should return 0 for same point."""
        service = HereEnrichmentService()
        distance = service._calculate_distance(-23.5505, -46.6333, -23.5505, -46.6333)
        assert distance == 0

    def test_calculate_distance_known_distance(self):
        """It should calculate correct distance for known points."""
        service = HereEnrichmentService()
        # São Paulo to Rio de Janeiro (approximately 360km)
        distance = service._calculate_distance(
            -23.5505, -46.6333,  # São Paulo
            -22.9068, -43.1729   # Rio de Janeiro
        )
        # Distance should be around 360km (360000m)
        assert 350000 < distance < 380000

    def test_calculate_distance_short_distance(self):
        """It should calculate correct distance for nearby points."""
        service = HereEnrichmentService()
        # Points approximately 100m apart
        distance = service._calculate_distance(
            -23.5505, -46.6333,
            -23.5514, -46.6333  # ~100m south
        )
        assert 90 < distance < 110


class TestFindBestMatch:
    """Test best match finding logic."""

    def test_find_best_match_exact_name(self):
        """It should find exact name match."""
        service = HereEnrichmentService()

        db_poi = MockDBPoi(name="Posto Shell Centro")
        search_location = GeoLocation(latitude=-23.5505, longitude=-46.6333)

        here_pois = [
            POI(
                id="here1",
                name="Posto Shell Centro",
                location=GeoLocation(latitude=-23.5506, longitude=-46.6334),
                category=POICategory.GAS_STATION,
            ),
            POI(
                id="here2",
                name="Posto Ipiranga",
                location=GeoLocation(latitude=-23.5510, longitude=-46.6340),
                category=POICategory.GAS_STATION,
            ),
        ]

        result = service._find_best_match(db_poi, here_pois, search_location)

        assert result is not None
        assert result[0].name == "Posto Shell Centro"

    def test_find_best_match_partial_name(self):
        """It should find partial name match."""
        service = HereEnrichmentService()

        db_poi = MockDBPoi(name="Shell")
        search_location = GeoLocation(latitude=-23.5505, longitude=-46.6333)

        here_pois = [
            POI(
                id="here1",
                name="Posto Shell Centro",
                location=GeoLocation(latitude=-23.5506, longitude=-46.6334),
                category=POICategory.GAS_STATION,
            ),
        ]

        result = service._find_best_match(db_poi, here_pois, search_location)

        assert result is not None
        assert "Shell" in result[0].name

    def test_find_best_match_closest_when_no_name_match(self):
        """It should return closest POI when no good name match and very close."""
        service = HereEnrichmentService()

        db_poi = MockDBPoi(name="XYZ Fuel Station")
        search_location = GeoLocation(latitude=-23.5505, longitude=-46.6333)

        here_pois = [
            POI(
                id="here1",
                name="ABC Gas Station",
                location=GeoLocation(latitude=-23.5505, longitude=-46.6333),  # Same location
                category=POICategory.GAS_STATION,
            ),
        ]

        result = service._find_best_match(db_poi, here_pois, search_location)

        # Should return closest one when it's very close (< 50m)
        assert result is not None

    def test_find_best_match_no_match_when_far(self):
        """It should return None when no good match and POIs are far."""
        service = HereEnrichmentService()

        db_poi = MockDBPoi(name="Unique Name XYZ")
        search_location = GeoLocation(latitude=-23.5505, longitude=-46.6333)

        here_pois = [
            POI(
                id="here1",
                name="Completely Different Name",
                location=GeoLocation(latitude=-23.5600, longitude=-46.6400),  # Far away
                category=POICategory.GAS_STATION,
            ),
        ]

        result = service._find_best_match(db_poi, here_pois, search_location)

        # Should return None when no good match
        assert result is None

    def test_find_best_match_empty_list(self):
        """It should return None for empty POI list."""
        service = HereEnrichmentService()

        db_poi = MockDBPoi(name="Test POI")
        search_location = GeoLocation(latitude=-23.5505, longitude=-46.6333)

        result = service._find_best_match(db_poi, [], search_location)

        assert result is None


class TestEnrichPoi:
    """Test single POI enrichment."""

    @pytest.mark.asyncio
    async def test_enrich_poi_disabled(self):
        """It should return error when enrichment is disabled."""
        service = HereEnrichmentService()
        # Manually disable by setting API key to None
        original_key = service.settings.here_api_key
        service.settings.here_api_key = None

        poi = MockDBPoi()

        result = await service.enrich_poi(poi)

        assert result.matched is False
        assert "disabled" in result.error.lower()

        # Restore
        service.settings.here_api_key = original_key

    @pytest.mark.asyncio
    async def test_enrich_poi_already_enriched(self):
        """It should skip already enriched POIs."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_key'}):
            from api.providers.settings import reset_settings
            reset_settings()

            service = HereEnrichmentService()
            poi = MockDBPoi(here_id="existing_here_id", enriched_by=["here_maps"])

            result = await service.enrich_poi(poi)

            assert result.matched is True
            assert result.here_id == "existing_here_id"
            assert "Already enriched" in result.error

    @pytest.mark.asyncio
    async def test_enrich_poi_no_results(self):
        """It should handle no matching HERE POIs."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_key'}):
            from api.providers.settings import reset_settings
            reset_settings()

            service = HereEnrichmentService()
            poi = MockDBPoi()

            # Mock HERE provider to return empty results
            mock_here_provider = AsyncMock()
            mock_here_provider.search_pois = AsyncMock(return_value=[])
            service._here_provider = mock_here_provider

            result = await service.enrich_poi(poi)

            assert result.matched is False
            assert "No HERE results" in result.error

    @pytest.mark.asyncio
    async def test_enrich_poi_successful_match(self):
        """It should successfully enrich POI with HERE data."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_key'}):
            from api.providers.settings import reset_settings
            reset_settings()

            service = HereEnrichmentService()
            poi = MockDBPoi(name="Posto Shell")

            # Mock HERE provider
            mock_here_poi = POI(
                id="here_123",
                name="Posto Shell Centro",
                location=GeoLocation(latitude=-23.5505, longitude=-46.6333),
                category=POICategory.GAS_STATION,
                phone="+55 11 1234-5678",
                website="https://shell.com.br",
                opening_hours={"general": "Seg-Dom: 00:00-24:00"},  # String, not list
                provider_data={"here_id": "here_123"}
            )

            mock_here_provider = AsyncMock()
            mock_here_provider.search_pois = AsyncMock(return_value=[mock_here_poi])
            service._here_provider = mock_here_provider

            result = await service.enrich_poi(poi)

            assert result.matched is True
            assert result.here_id == "here_123"
            assert result.phone == "+55 11 1234-5678"
            assert result.website == "https://shell.com.br"


class TestEnrichPois:
    """Test batch POI enrichment."""

    @pytest.mark.asyncio
    async def test_enrich_pois_disabled(self):
        """It should return empty list when disabled."""
        service = HereEnrichmentService()
        # Manually disable by setting API key to None
        original_key = service.settings.here_api_key
        service.settings.here_api_key = None

        pois = [MockDBPoi(), MockDBPoi()]

        results = await service.enrich_pois(pois)

        assert results == []

        # Restore
        service.settings.here_api_key = original_key

    @pytest.mark.asyncio
    async def test_enrich_pois_filters_enrichable(self):
        """It should only enrich enrichable POIs."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_key'}):
            from api.providers.settings import reset_settings
            reset_settings()

            service = HereEnrichmentService()

            pois = [
                MockDBPoi(id="1", poi_type="gas_station"),
                MockDBPoi(id="2", poi_type="unknown_type"),  # Not enrichable
                MockDBPoi(id="3", poi_type="restaurant"),
            ]

            # Mock HERE provider
            mock_here_provider = AsyncMock()
            mock_here_provider.search_pois = AsyncMock(return_value=[])
            service._here_provider = mock_here_provider

            results = await service.enrich_pois(pois, delay_between_requests=0)

            # Should only process enrichable POIs
            assert len(results) == 2


class TestHereEnrichmentResult:
    """Test HereEnrichmentResult dataclass."""

    def test_result_creation_success(self):
        """It should create successful result."""
        result = HereEnrichmentResult(
            poi_id="poi_1",
            osm_id="node/123",
            here_id="here_456",
            matched=True,
            phone="+55 11 1234-5678",
            website="https://example.com",
            match_distance_meters=25.5
        )

        assert result.matched is True
        assert result.poi_id == "poi_1"
        assert result.here_id == "here_456"
        assert result.error is None

    def test_result_creation_failure(self):
        """It should create failure result."""
        result = HereEnrichmentResult(
            poi_id="poi_1",
            osm_id="node/123",
            here_id=None,
            matched=False,
            error="No matching POI found"
        )

        assert result.matched is False
        assert result.here_id is None
        assert result.error == "No matching POI found"
