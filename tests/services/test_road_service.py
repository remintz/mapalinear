"""
Tests for RoadService - TDD Implementation.

This module contains comprehensive tests for the RoadService class,
covering the main map generation functionality and helper methods.
"""

import pytest
import math
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Tuple

from api.services.road_service import RoadService
from api.providers.base import GeoProvider, ProviderType
from api.providers.models import GeoLocation, Route, POI, POICategory
from api.models.road_models import (
    LinearMapResponse,
    LinearRoadSegment,
    RoadMilestone,
    MilestoneType,
    Coordinates,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_geo_provider():
    """Create a mock geo provider for routing/geocoding."""
    provider = Mock(spec=GeoProvider)
    provider.provider_type = ProviderType.OSM
    provider.geocode = AsyncMock()
    provider.reverse_geocode = AsyncMock()
    provider.calculate_route = AsyncMock()
    provider.search_pois = AsyncMock()
    return provider


@pytest.fixture
def mock_poi_provider():
    """Create a mock POI provider."""
    provider = Mock(spec=GeoProvider)
    provider.provider_type = ProviderType.OSM
    provider.search_pois = AsyncMock()
    return provider


@pytest.fixture
def road_service(mock_geo_provider, mock_poi_provider):
    """Create RoadService with mocked providers."""
    return RoadService(
        geo_provider=mock_geo_provider,
        poi_provider=mock_poi_provider
    )


@pytest.fixture
def sample_origin_location():
    """Sample origin location (São Paulo)."""
    return GeoLocation(
        latitude=-23.5505,
        longitude=-46.6333,
        address="São Paulo, SP, Brasil",
        city="São Paulo",
        state="SP",
        country="Brasil"
    )


@pytest.fixture
def sample_destination_location():
    """Sample destination location (Rio de Janeiro)."""
    return GeoLocation(
        latitude=-22.9068,
        longitude=-43.1729,
        address="Rio de Janeiro, RJ, Brasil",
        city="Rio de Janeiro",
        state="RJ",
        country="Brasil"
    )


@pytest.fixture
def sample_route(sample_origin_location, sample_destination_location):
    """Sample route between SP and RJ."""
    from api.providers.models import RouteStep

    return Route(
        origin=sample_origin_location,
        destination=sample_destination_location,
        total_distance=430.5,
        total_duration=300.0,
        geometry=[
            (-23.5505, -46.6333),  # São Paulo
            (-23.2000, -45.5000),  # Intermediate 1
            (-23.0000, -44.5000),  # Intermediate 2
            (-22.9068, -43.1729),  # Rio de Janeiro
        ],
        road_names=["BR-116", "Via Dutra"],
        steps=[
            RouteStep(
                distance_m=215000.0,
                duration_s=10800.0,
                geometry=[
                    (-23.5505, -46.6333),
                    (-23.2000, -45.5000),
                    (-23.0000, -44.5000),
                ],
                road_name="BR-116",
                maneuver_type="depart",
                maneuver_modifier=None,
                maneuver_location=(-23.5505, -46.6333),
            ),
            RouteStep(
                distance_m=215500.0,
                duration_s=10800.0,
                geometry=[
                    (-23.0000, -44.5000),
                    (-22.9068, -43.1729),
                ],
                road_name="Via Dutra",
                maneuver_type="arrive",
                maneuver_modifier=None,
                maneuver_location=(-23.0000, -44.5000),
            ),
        ],
    )


@pytest.fixture
def sample_pois():
    """Sample POIs for testing."""
    return [
        POI(
            id="node/123456",
            name="Posto Shell Centro",
            location=GeoLocation(latitude=-23.3000, longitude=-45.2000),
            category=POICategory.GAS_STATION,
            amenities=["24h", "Loja"],
            rating=4.2,
            phone="+55 11 1234-5678",
            provider_data={'osm_tags': {'amenity': 'fuel', 'brand': 'Shell'}}
        ),
        POI(
            id="node/123457",
            name="Restaurante Família",
            location=GeoLocation(latitude=-23.1000, longitude=-44.8000),
            category=POICategory.RESTAURANT,
            amenities=["Estacionamento", "WiFi"],
            rating=4.5,
            provider_data={'osm_tags': {'amenity': 'restaurant', 'cuisine': 'brazilian'}}
        ),
        POI(
            id="node/123458",
            name="Hotel Beira Estrada",
            location=GeoLocation(latitude=-23.0500, longitude=-44.3000),
            category=POICategory.HOTEL,
            amenities=["WiFi", "Café da manhã"],
            rating=3.8,
            provider_data={'osm_tags': {'tourism': 'hotel'}}
        ),
    ]


# =============================================================================
# TEST: INITIALIZATION
# =============================================================================

class TestRoadServiceInitialization:
    """Test RoadService initialization."""

    def test_init_with_default_providers(self):
        """It should initialize with default OSM providers."""
        with patch('api.providers.create_provider') as mock_create:
            mock_provider = Mock()
            mock_provider.provider_type = ProviderType.OSM
            mock_create.return_value = mock_provider

            service = RoadService()

            assert service.geo_provider is not None
            assert service.poi_provider is not None

    def test_init_with_custom_providers(self, mock_geo_provider, mock_poi_provider):
        """It should accept custom providers."""
        service = RoadService(
            geo_provider=mock_geo_provider,
            poi_provider=mock_poi_provider
        )

        assert service.geo_provider == mock_geo_provider
        assert service.poi_provider == mock_poi_provider


# =============================================================================
# TEST: UTILITY METHODS
# =============================================================================

class TestExtractCityName:
    """Test _extract_city_name method."""

    def test_extract_city_from_full_address(self, road_service):
        """It should extract city name from 'City, State' format."""
        result = road_service._extract_city_name("São Paulo, SP")
        assert result == "São Paulo"

    def test_extract_city_from_city_only(self, road_service):
        """It should handle city-only input."""
        result = road_service._extract_city_name("Campinas")
        assert result == "Campinas"

    def test_extract_city_strips_whitespace(self, road_service):
        """It should strip whitespace."""
        result = road_service._extract_city_name("  Rio de Janeiro  , RJ  ")
        assert result == "Rio de Janeiro"


class TestCalculateDistanceMeters:
    """Test _calculate_distance_meters (Haversine) method."""

    def test_same_point_returns_zero(self, road_service):
        """It should return 0 for same point."""
        distance = road_service._calculate_distance_meters(
            -23.5505, -46.6333,
            -23.5505, -46.6333
        )
        assert distance == 0.0

    def test_known_distance_sao_paulo_to_rio(self, road_service):
        """It should calculate approximately correct distance SP to RJ."""
        # Direct line distance is ~357 km
        distance = road_service._calculate_distance_meters(
            -23.5505, -46.6333,  # São Paulo
            -22.9068, -43.1729   # Rio de Janeiro
        )
        # Convert to km and check roughly correct (350-370 km)
        distance_km = distance / 1000
        assert 350 < distance_km < 370

    def test_short_distance(self, road_service):
        """It should calculate short distances accurately."""
        # Two points ~100m apart
        distance = road_service._calculate_distance_meters(
            -23.5505, -46.6333,
            -23.5505, -46.6323  # ~100m east
        )
        assert 90 < distance < 120  # Should be around 100m


class TestInterpolateCoordinateAtDistance:
    """Test _interpolate_coordinate_at_distance method."""

    def test_at_start_returns_first_point(self, road_service):
        """It should return first point at distance 0."""
        geometry = [(-23.5505, -46.6333), (-22.9068, -43.1729)]

        result = road_service._interpolate_coordinate_at_distance(
            geometry, 0.0, 430.0
        )

        assert result == (-23.5505, -46.6333)

    def test_at_end_returns_last_point(self, road_service):
        """It should return last point at total distance."""
        geometry = [(-23.5505, -46.6333), (-22.9068, -43.1729)]

        result = road_service._interpolate_coordinate_at_distance(
            geometry, 430.0, 430.0
        )

        assert result == (-22.9068, -43.1729)

    def test_at_midpoint_interpolates(self, road_service):
        """It should interpolate at midpoint."""
        geometry = [(-23.5505, -46.6333), (-22.9068, -43.1729)]

        result = road_service._interpolate_coordinate_at_distance(
            geometry, 215.0, 430.0
        )

        # Should be roughly between the two points
        assert -23.5505 < result[0] < -22.9068
        assert -46.6333 < result[1] < -43.1729

    def test_empty_geometry_returns_zero(self, road_service):
        """It should return (0,0) for empty geometry."""
        result = road_service._interpolate_coordinate_at_distance(
            [], 100.0, 430.0
        )
        assert result == (0.0, 0.0)


# =============================================================================
# TEST: PROCESS ROUTE INTO SEGMENTS
# =============================================================================

class TestProcessRouteIntoSegments:
    """Test _process_route_into_segments method."""

    def test_creates_correct_number_of_segments(self, road_service, sample_route):
        """It should create correct number of segments based on length."""
        # 430.5 km / 10 km per segment = ~44 segments
        segments = road_service._process_route_into_segments(sample_route, 10.0)

        assert len(segments) == 44

    def test_segment_distances_are_continuous(self, road_service, sample_route):
        """It should create continuous segments."""
        segments = road_service._process_route_into_segments(sample_route, 50.0)

        for i in range(len(segments) - 1):
            assert segments[i].end_distance_km == segments[i + 1].start_distance_km

    def test_first_segment_starts_at_zero(self, road_service, sample_route):
        """It should start first segment at 0."""
        segments = road_service._process_route_into_segments(sample_route, 50.0)

        assert segments[0].start_distance_km == 0.0

    def test_last_segment_ends_at_total_distance(self, road_service, sample_route):
        """It should end last segment at total distance."""
        segments = road_service._process_route_into_segments(sample_route, 50.0)

        assert segments[-1].end_distance_km == sample_route.total_distance

    def test_segments_have_coordinates(self, road_service, sample_route):
        """It should include start/end coordinates in segments."""
        segments = road_service._process_route_into_segments(sample_route, 100.0)

        for segment in segments:
            assert segment.start_coordinates is not None
            assert segment.end_coordinates is not None
            assert segment.start_coordinates.latitude != 0
            assert segment.start_coordinates.longitude != 0

    def test_segments_have_road_name(self, road_service, sample_route):
        """It should include road name in segments."""
        segments = road_service._process_route_into_segments(sample_route, 100.0)

        for segment in segments:
            assert segment.name == "BR-116"  # First road name from route

    def test_single_segment_for_short_route(self, road_service):
        """It should create single segment for route shorter than segment length."""
        short_route = Route(
            origin=GeoLocation(latitude=-23.55, longitude=-46.63),
            destination=GeoLocation(latitude=-23.56, longitude=-46.64),
            total_distance=5.0,
            total_duration=10.0,
            geometry=[(-23.55, -46.63), (-23.56, -46.64)],
            road_names=["Rua Teste"]
        )

        segments = road_service._process_route_into_segments(short_route, 10.0)

        assert len(segments) == 1
        assert segments[0].length_km == 5.0


# =============================================================================
# TEST: EXTRACT SEARCH POINTS
# =============================================================================

class TestExtractSearchPointsFromSegments:
    """Test _extract_search_points_from_segments method."""

    def test_extracts_start_points_from_all_segments(self, road_service, sample_route):
        """It should extract start point from each segment."""
        segments = road_service._process_route_into_segments(sample_route, 100.0)

        search_points = road_service._extract_search_points_from_segments(segments)

        # Should have 5 segments + 1 end point = 6 points for 430km route with 100km segments
        assert len(search_points) >= len(segments)

    def test_includes_last_segment_end_point(self, road_service, sample_route):
        """It should include end point of last segment."""
        segments = road_service._process_route_into_segments(sample_route, 100.0)

        search_points = road_service._extract_search_points_from_segments(segments)

        # Last point should be at total distance
        last_point = search_points[-1]
        assert abs(last_point[1] - sample_route.total_distance) < 1.0

    def test_search_points_have_coordinates_and_distance(self, road_service, sample_route):
        """It should return tuples of (coords, distance)."""
        segments = road_service._process_route_into_segments(sample_route, 100.0)

        search_points = road_service._extract_search_points_from_segments(segments)

        for point in search_points:
            coords, distance = point
            assert isinstance(coords, tuple)
            assert len(coords) == 2
            assert isinstance(distance, float)


# =============================================================================
# TEST: GENERATE LINEAR MAP (MAIN METHOD)
# =============================================================================

class TestGenerateLinearMap:
    """Test generate_linear_map main method."""

    @patch('api.services.road_service._is_debug_enabled_sync', return_value=False)
    @patch('api.services.map_storage_service_db.save_map_sync', return_value="test-map-id")
    def test_generates_map_successfully(
        self, mock_save, mock_debug,
        road_service, mock_geo_provider, mock_poi_provider,
        sample_origin_location, sample_destination_location, sample_route, sample_pois
    ):
        """It should generate a complete linear map."""
        # Setup mocks
        mock_geo_provider.geocode.side_effect = [
            sample_origin_location,
            sample_destination_location
        ]
        mock_geo_provider.calculate_route.return_value = sample_route
        mock_poi_provider.search_pois.return_value = sample_pois

        # Mock the segment processing method
        with patch.object(road_service, '_process_steps_into_segments') as mock_segments:
            # Return empty segments and POIs for this unit test
            mock_segments.return_value = ([], [])

            result = road_service.generate_linear_map(
                origin="São Paulo, SP",
                destination="Rio de Janeiro, RJ"
            )

        assert isinstance(result, LinearMapResponse)
        assert result.origin == "São Paulo, SP"
        assert result.destination == "Rio de Janeiro, RJ"
        assert result.total_length_km == sample_route.total_distance
        assert len(result.segments) > 0

    @patch('api.services.road_service._is_debug_enabled_sync', return_value=False)
    def test_raises_error_for_invalid_origin(
        self, mock_debug,
        road_service, mock_geo_provider
    ):
        """It should raise error if origin cannot be geocoded."""
        mock_geo_provider.geocode.return_value = None

        with pytest.raises(ValueError, match="Could not geocode"):
            road_service.generate_linear_map(
                origin="Invalid Place",
                destination="Rio de Janeiro, RJ"
            )

    @patch('api.services.road_service._is_debug_enabled_sync', return_value=False)
    def test_raises_error_for_invalid_destination(
        self, mock_debug,
        road_service, mock_geo_provider, sample_origin_location
    ):
        """It should raise error if destination cannot be geocoded."""
        mock_geo_provider.geocode.side_effect = [sample_origin_location, None]

        with pytest.raises(ValueError, match="Could not geocode"):
            road_service.generate_linear_map(
                origin="São Paulo, SP",
                destination="Invalid Place"
            )

    @patch('api.services.road_service._is_debug_enabled_sync', return_value=False)
    def test_raises_error_if_route_not_found(
        self, mock_debug,
        road_service, mock_geo_provider,
        sample_origin_location, sample_destination_location
    ):
        """It should raise error if route cannot be calculated."""
        mock_geo_provider.geocode.side_effect = [
            sample_origin_location,
            sample_destination_location
        ]
        mock_geo_provider.calculate_route.return_value = None

        with pytest.raises(ValueError, match="Could not calculate route"):
            road_service.generate_linear_map(
                origin="São Paulo, SP",
                destination="Rio de Janeiro, RJ"
            )


# =============================================================================
# TEST: GEOCODE AND VALIDATE
# =============================================================================

class TestGeocodeAndValidate:
    """Test _geocode_and_validate method."""

    def test_returns_location_on_success(self, road_service, mock_geo_provider, sample_origin_location):
        """It should return location on successful geocode."""
        mock_geo_provider.geocode.return_value = sample_origin_location

        result = road_service._geocode_and_validate("São Paulo, SP", "origem")

        assert result == sample_origin_location

    def test_raises_on_failure(self, road_service, mock_geo_provider):
        """It should raise ValueError on geocode failure."""
        mock_geo_provider.geocode.return_value = None

        with pytest.raises(ValueError, match="Could not geocode"):
            road_service._geocode_and_validate("Invalid Place", "origem")


# =============================================================================
# TEST: ASYNC METHODS
# =============================================================================

class TestAsyncMethods:
    """Test async methods of RoadService."""

    @pytest.mark.asyncio
    async def test_geocode_location_async_success(self, road_service, mock_geo_provider, sample_origin_location):
        """It should geocode location asynchronously."""
        mock_geo_provider.geocode.return_value = sample_origin_location

        result = await road_service.geocode_location_async("São Paulo, SP")

        assert result == (sample_origin_location.latitude, sample_origin_location.longitude)

    @pytest.mark.asyncio
    async def test_geocode_location_async_failure(self, road_service, mock_geo_provider):
        """It should return None on geocode failure."""
        mock_geo_provider.geocode.return_value = None

        result = await road_service.geocode_location_async("Invalid")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_pois_async_success(self, road_service, mock_poi_provider, sample_pois):
        """It should search POIs asynchronously."""
        mock_poi_provider.search_pois.return_value = sample_pois

        result = await road_service.search_pois_async(
            location=(-23.5505, -46.6333),
            radius=1000,
            categories=['gas_station']
        )

        assert len(result) == len(sample_pois)

    @pytest.mark.asyncio
    async def test_search_pois_async_error_returns_empty(self, road_service, mock_poi_provider):
        """It should return empty list on error."""
        mock_poi_provider.search_pois.side_effect = Exception("Network error")

        result = await road_service.search_pois_async(
            location=(-23.5505, -46.6333),
            radius=1000,
            categories=['gas_station']
        )

        assert result == []
