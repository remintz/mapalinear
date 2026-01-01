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
        road_names=["BR-116", "Via Dutra"]
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
# TEST: POI CATEGORY TO MILESTONE TYPE CONVERSION
# =============================================================================

class TestPOICategoryToMilestoneType:
    """Test _poi_category_to_milestone_type method."""

    def test_gas_station_mapping(self, road_service):
        """It should map GAS_STATION to GAS_STATION."""
        result = road_service._poi_category_to_milestone_type(POICategory.GAS_STATION)
        assert result == MilestoneType.GAS_STATION

    def test_restaurant_mapping(self, road_service):
        """It should map RESTAURANT to RESTAURANT."""
        result = road_service._poi_category_to_milestone_type(POICategory.RESTAURANT)
        assert result == MilestoneType.RESTAURANT

    def test_hotel_mapping(self, road_service):
        """It should map HOTEL to HOTEL."""
        result = road_service._poi_category_to_milestone_type(POICategory.HOTEL)
        assert result == MilestoneType.HOTEL

    def test_hospital_mapping(self, road_service):
        """It should map HOSPITAL to HOSPITAL."""
        result = road_service._poi_category_to_milestone_type(POICategory.HOSPITAL)
        assert result == MilestoneType.HOSPITAL


# =============================================================================
# TEST: CREATE MILESTONE FROM POI
# =============================================================================

class TestCreateMilestoneFromPOI:
    """Test _create_milestone_from_poi method."""

    def test_creates_milestone_with_basic_info(self, road_service, sample_pois):
        """It should create milestone with correct basic info."""
        poi = sample_pois[0]  # Gas station
        route_point = (-23.3000, -45.2000)

        milestone = road_service._create_milestone_from_poi(
            poi,
            distance_from_origin=150.0,
            route_point=route_point
        )

        assert milestone.id == poi.id
        assert milestone.name == poi.name
        assert milestone.type == MilestoneType.GAS_STATION
        assert milestone.distance_from_origin_km == 150.0

    def test_includes_coordinates(self, road_service, sample_pois):
        """It should include POI coordinates."""
        poi = sample_pois[0]

        milestone = road_service._create_milestone_from_poi(
            poi,
            distance_from_origin=100.0,
            route_point=(-23.3000, -45.2000)
        )

        assert milestone.coordinates.latitude == poi.location.latitude
        assert milestone.coordinates.longitude == poi.location.longitude

    def test_includes_amenities(self, road_service, sample_pois):
        """It should include amenities from POI."""
        poi = sample_pois[0]

        milestone = road_service._create_milestone_from_poi(
            poi,
            distance_from_origin=100.0,
            route_point=(-23.3000, -45.2000)
        )

        assert milestone.amenities == poi.amenities

    def test_includes_phone(self, road_service, sample_pois):
        """It should include phone from POI."""
        poi = sample_pois[0]

        milestone = road_service._create_milestone_from_poi(
            poi,
            distance_from_origin=100.0,
            route_point=(-23.3000, -45.2000)
        )

        assert milestone.phone == poi.phone

    def test_handles_junction_info(self, road_service):
        """It should handle junction info for distant POIs."""
        # Create POI that is far from route (> 500m)
        distant_poi = POI(
            id="node/999",
            name="Posto Distante",
            location=GeoLocation(latitude=-23.3100, longitude=-45.2100),  # ~1.5km from route
            category=POICategory.GAS_STATION,
            amenities=["24h"],
            provider_data={'osm_tags': {'amenity': 'fuel'}}
        )
        # Route point is different from POI location (simulating distant POI)
        route_point = (-23.3000, -45.2000)
        junction_info = (150.0, (-23.2900, -45.1900), 2.5, "right")

        milestone = road_service._create_milestone_from_poi(
            distant_poi,
            distance_from_origin=150.0,
            route_point=route_point,
            junction_info=junction_info
        )

        assert milestone.junction_distance_km == 150.0
        assert milestone.junction_coordinates is not None
        # requires_detour is based on distance_from_road > 500m
        # The POI at (-23.31, -45.21) is ~1.5km from route_point (-23.30, -45.20)
        assert milestone.requires_detour == True
        assert milestone.side == "right"


# =============================================================================
# TEST: DETERMINE POI SIDE
# =============================================================================

class TestDeterminePOISide:
    """Test _determine_poi_side method."""

    def test_poi_on_right_side(self, road_service):
        """It should detect POI on right side of road."""
        # Road going north (increasing latitude)
        geometry = [(-23.5, -46.6), (-23.4, -46.6), (-23.3, -46.6)]
        junction = (-23.4, -46.6)
        poi_right = (-23.4, -46.5)  # East of road = right when going north

        side = road_service._determine_poi_side(geometry, junction, poi_right)

        assert side == "right"

    def test_poi_on_left_side(self, road_service):
        """It should detect POI on left side of road."""
        # Road going north (increasing latitude)
        geometry = [(-23.5, -46.6), (-23.4, -46.6), (-23.3, -46.6)]
        junction = (-23.4, -46.6)
        poi_left = (-23.4, -46.7)  # West of road = left when going north

        side = road_service._determine_poi_side(geometry, junction, poi_left)

        assert side == "left"


# =============================================================================
# TEST: CALCULATE DISTANCE ALONG ROUTE
# =============================================================================

class TestCalculateDistanceAlongRoute:
    """Test _calculate_distance_along_route method."""

    def test_point_at_start_returns_zero(self, road_service):
        """It should return 0 for point at route start."""
        geometry = [(-23.55, -46.63), (-23.45, -46.53), (-23.35, -46.43)]
        target = (-23.55, -46.63)

        distance = road_service._calculate_distance_along_route(geometry, target)

        assert distance < 1.0  # Should be close to 0

    def test_empty_geometry_returns_zero(self, road_service):
        """It should return 0 for empty geometry."""
        distance = road_service._calculate_distance_along_route([], (-23.5, -46.6))
        assert distance == 0.0


# =============================================================================
# TEST: FILTER EXCLUDED CITIES
# =============================================================================

class TestFilterExcludedCities:
    """Test _filter_excluded_cities method."""

    def test_filters_pois_in_excluded_city(self, road_service):
        """It should filter POIs in excluded cities."""
        milestones = [
            RoadMilestone(
                id="1", name="POI 1", type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.5, longitude=-46.6),
                distance_from_origin_km=10.0, distance_from_road_meters=100,
                side="right", city="São Paulo"
            ),
            RoadMilestone(
                id="2", name="POI 2", type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.3, longitude=-45.5),
                distance_from_origin_km=100.0, distance_from_road_meters=200,
                side="left", city="Campinas"
            ),
        ]

        filtered = road_service._filter_excluded_cities(milestones, ["são paulo"])

        assert len(filtered) == 1
        assert filtered[0].city == "Campinas"

    def test_keeps_pois_without_city(self, road_service):
        """It should keep POIs without city information."""
        milestones = [
            RoadMilestone(
                id="1", name="POI 1", type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.5, longitude=-46.6),
                distance_from_origin_km=10.0, distance_from_road_meters=100,
                side="right", city=None
            ),
        ]

        filtered = road_service._filter_excluded_cities(milestones, ["são paulo"])

        assert len(filtered) == 1

    def test_empty_exclude_list_returns_all(self, road_service):
        """It should return all milestones if exclude list is empty."""
        milestones = [
            RoadMilestone(
                id="1", name="POI 1", type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.5, longitude=-46.6),
                distance_from_origin_km=10.0, distance_from_road_meters=100,
                side="right", city="São Paulo"
            ),
        ]

        filtered = road_service._filter_excluded_cities(milestones, [])

        assert len(filtered) == 1


# =============================================================================
# TEST: ASSIGN MILESTONES TO SEGMENTS
# =============================================================================

class TestAssignMilestonesToSegments:
    """Test _assign_milestones_to_segments method."""

    def test_assigns_milestone_to_correct_segment(self, road_service):
        """It should assign milestone to segment containing its distance."""
        segments = [
            LinearRoadSegment(
                id="seg_1", name="Test", start_distance_km=0, end_distance_km=100,
                length_km=100, milestones=[]
            ),
            LinearRoadSegment(
                id="seg_2", name="Test", start_distance_km=100, end_distance_km=200,
                length_km=100, milestones=[]
            ),
        ]
        milestones = [
            RoadMilestone(
                id="1", name="POI", type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.5, longitude=-46.6),
                distance_from_origin_km=50.0, distance_from_road_meters=100,
                side="right"
            ),
            RoadMilestone(
                id="2", name="POI 2", type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.3, longitude=-45.5),
                distance_from_origin_km=150.0, distance_from_road_meters=200,
                side="left"
            ),
        ]

        road_service._assign_milestones_to_segments(segments, milestones)

        assert len(segments[0].milestones) == 1
        assert segments[0].milestones[0].id == "1"
        assert len(segments[1].milestones) == 1
        assert segments[1].milestones[0].id == "2"


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

        # Mock the async method
        with patch.object(road_service, '_find_milestones_from_segments', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []

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
# TEST: BUILD MILESTONE CATEGORIES
# =============================================================================

class TestBuildMilestoneCategories:
    """Test _build_milestone_categories method."""

    def test_includes_services_when_cities_requested(self, road_service):
        """It should include SERVICES category when include_cities=True."""
        categories = road_service._build_milestone_categories(include_cities=True)

        assert POICategory.SERVICES in categories

    def test_excludes_services_when_cities_not_requested(self, road_service):
        """It should exclude SERVICES category when include_cities=False."""
        categories = road_service._build_milestone_categories(include_cities=False)

        assert POICategory.SERVICES not in categories

    def test_always_includes_pois(self, road_service):
        """It should always include POI categories."""
        categories_with = road_service._build_milestone_categories(include_cities=True)
        categories_without = road_service._build_milestone_categories(include_cities=False)

        # Both should include gas stations, restaurants, etc.
        assert POICategory.GAS_STATION in categories_with
        assert POICategory.GAS_STATION in categories_without
        assert POICategory.RESTAURANT in categories_with
        assert POICategory.RESTAURANT in categories_without


# =============================================================================
# TEST: IS POI ABANDONED
# =============================================================================

class TestIsPOIAbandoned:
    """Test _is_poi_abandoned method."""

    def test_detects_abandoned_yes(self, road_service):
        """It should detect abandoned=yes."""
        tags = {'abandoned': 'yes', 'amenity': 'fuel'}
        assert road_service._is_poi_abandoned(tags) == True

    def test_detects_disused_yes(self, road_service):
        """It should detect disused=yes."""
        tags = {'disused': 'yes', 'amenity': 'fuel'}
        assert road_service._is_poi_abandoned(tags) == True

    def test_detects_disused_prefix(self, road_service):
        """It should detect disused: prefix in amenity."""
        tags = {'disused:amenity': 'fuel'}
        assert road_service._is_poi_abandoned(tags) == True

    def test_normal_poi_not_abandoned(self, road_service):
        """It should return False for normal POIs."""
        tags = {'amenity': 'fuel', 'brand': 'Shell'}
        assert road_service._is_poi_abandoned(tags) == False


# =============================================================================
# TEST: CALCULATE POI QUALITY SCORE
# =============================================================================

class TestCalculatePOIQualityScore:
    """Test _calculate_poi_quality_score method."""

    def test_empty_tags_returns_base_score(self, road_service):
        """It should return base score for empty tags."""
        score = road_service._calculate_poi_quality_score({})
        assert score >= 0.0
        assert score <= 1.0

    def test_more_info_higher_score(self, road_service):
        """It should give higher score to POIs with more info."""
        basic_tags = {'amenity': 'fuel'}
        rich_tags = {
            'amenity': 'fuel',
            'name': 'Posto Shell',
            'brand': 'Shell',
            'phone': '+55 11 1234',
            'opening_hours': '24/7',
            'website': 'https://shell.com'
        }

        basic_score = road_service._calculate_poi_quality_score(basic_tags)
        rich_score = road_service._calculate_poi_quality_score(rich_tags)

        assert rich_score > basic_score


# =============================================================================
# TEST: EXTRACT AMENITIES
# =============================================================================

class TestExtractAmenities:
    """Test _extract_amenities method."""

    def test_extracts_24h_from_opening_hours(self, road_service):
        """It should detect 24h operation."""
        tags = {'opening_hours': '24/7'}
        amenities = road_service._extract_amenities(tags)
        assert '24h' in amenities

    def test_extracts_fuel_types(self, road_service):
        """It should extract fuel type information."""
        tags = {'fuel:diesel': 'yes', 'fuel:octane_95': 'yes'}
        amenities = road_service._extract_amenities(tags)
        # Should contain fuel-related amenities
        assert any('diesel' in a.lower() or 'Diesel' in a for a in amenities)

    def test_extracts_shop(self, road_service):
        """It should detect convenience shop when marked as yes."""
        # The _extract_amenities method checks if tag value is 'yes', 'true', '1', or 'available'
        tags = {'shop': 'yes'}
        amenities = road_service._extract_amenities(tags)
        assert any('loja' in a.lower() for a in amenities)


# =============================================================================
# TEST: FORMAT OPENING HOURS
# =============================================================================

class TestFormatOpeningHours:
    """Test _format_opening_hours method."""

    def test_none_returns_none(self, road_service):
        """It should return None for None input."""
        result = road_service._format_opening_hours(None)
        assert result is None

    def test_dict_formats_correctly(self, road_service):
        """It should format dict opening hours."""
        hours = {'mon': '09:00-18:00', 'tue': '09:00-18:00'}
        result = road_service._format_opening_hours(hours)
        assert result is not None
        assert 'mon' in result or '09:00' in result


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

    @pytest.mark.asyncio
    async def test_enrich_milestones_with_cities(self, road_service, mock_geo_provider):
        """It should enrich milestones with city information."""
        milestones = [
            RoadMilestone(
                id="1", name="POI 1", type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.5, longitude=-46.6),
                distance_from_origin_km=10.0, distance_from_road_meters=100,
                side="right", city=None  # No city initially
            ),
        ]

        mock_geo_provider.reverse_geocode.return_value = GeoLocation(
            latitude=-23.5, longitude=-46.6,
            address="Test", city="São Paulo"
        )

        await road_service._enrich_milestones_with_cities(milestones)

        assert milestones[0].city == "São Paulo"
