"""
Unit tests for api/services/milestone_factory.py

Tests for milestone creation and management:
- get_milestone_type (category conversion)
- build_milestone_categories
- create_from_poi
- assign_to_segments
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from api.models.road_models import Coordinates, LinearRoadSegment, MilestoneType, RoadMilestone
from api.providers.models import GeoLocation, POI, POICategory
from api.services.milestone_factory import (
    MilestoneFactory,
    get_milestone_type,
    build_milestone_categories,
    assign_milestones_to_segments,
    POI_CATEGORY_TO_MILESTONE_TYPE,
)


class TestGetMilestoneType:
    """Tests for POI category to milestone type conversion."""

    def test_gas_station_category(self):
        """GAS_STATION should map to GAS_STATION milestone."""
        assert get_milestone_type(POICategory.GAS_STATION) == MilestoneType.GAS_STATION

    def test_fuel_category(self):
        """FUEL should map to GAS_STATION milestone."""
        assert get_milestone_type(POICategory.FUEL) == MilestoneType.GAS_STATION

    def test_restaurant_category(self):
        """RESTAURANT should map to RESTAURANT milestone."""
        assert get_milestone_type(POICategory.RESTAURANT) == MilestoneType.RESTAURANT

    def test_food_category(self):
        """FOOD should map to RESTAURANT milestone."""
        assert get_milestone_type(POICategory.FOOD) == MilestoneType.RESTAURANT

    def test_hotel_category(self):
        """HOTEL should map to HOTEL milestone."""
        assert get_milestone_type(POICategory.HOTEL) == MilestoneType.HOTEL

    def test_lodging_category(self):
        """LODGING should map to HOTEL milestone."""
        assert get_milestone_type(POICategory.LODGING) == MilestoneType.HOTEL

    def test_camping_category(self):
        """CAMPING should map to CAMPING milestone."""
        assert get_milestone_type(POICategory.CAMPING) == MilestoneType.CAMPING

    def test_hospital_category(self):
        """HOSPITAL should map to HOSPITAL milestone."""
        assert get_milestone_type(POICategory.HOSPITAL) == MilestoneType.HOSPITAL

    def test_services_category(self):
        """SERVICES should map to OTHER milestone."""
        assert get_milestone_type(POICategory.SERVICES) == MilestoneType.OTHER

    def test_parking_category(self):
        """PARKING should map to OTHER milestone."""
        assert get_milestone_type(POICategory.PARKING) == MilestoneType.OTHER

    def test_unknown_category_returns_other(self):
        """Unknown category should map to OTHER."""
        # Create a mock category not in mapping
        mock_category = MagicMock()
        mock_category.value = "unknown"
        result = POI_CATEGORY_TO_MILESTONE_TYPE.get(mock_category, MilestoneType.OTHER)
        assert result == MilestoneType.OTHER


class TestBuildMilestoneCategories:
    """Tests for building POI category lists."""

    def test_includes_basic_categories(self):
        """Should include basic POI categories."""
        categories = build_milestone_categories()
        assert POICategory.GAS_STATION in categories
        assert POICategory.RESTAURANT in categories
        assert POICategory.HOTEL in categories

    def test_includes_cities_by_default(self):
        """Should include SERVICES (cities) by default."""
        categories = build_milestone_categories()
        assert POICategory.SERVICES in categories

    def test_excludes_cities_when_disabled(self):
        """Should exclude SERVICES when include_cities=False."""
        categories = build_milestone_categories(include_cities=False)
        assert POICategory.SERVICES not in categories

    def test_includes_all_fuel_types(self):
        """Should include both GAS_STATION and FUEL categories."""
        categories = build_milestone_categories()
        assert POICategory.GAS_STATION in categories
        assert POICategory.FUEL in categories

    def test_includes_hospital(self):
        """Should include hospital category."""
        categories = build_milestone_categories()
        assert POICategory.HOSPITAL in categories

    def test_includes_camping(self):
        """Should include camping category."""
        categories = build_milestone_categories()
        assert POICategory.CAMPING in categories


class TestMilestoneFactoryCreateFromPOI:
    """Tests for creating milestones from POIs."""

    @pytest.fixture
    def factory(self):
        """Create factory instance."""
        return MilestoneFactory()

    @pytest.fixture
    def sample_poi(self):
        """Create a sample POI."""
        return POI(
            id="poi_123",
            name="Posto Shell",
            category=POICategory.GAS_STATION,
            location=GeoLocation(latitude=-23.5505, longitude=-46.6333),
            provider_data={
                "osm_tags": {"amenity": "fuel", "brand": "Shell"},
                "quality_score": 0.8,
            },
            subcategory="Shell",
            phone="+55 11 1234-5678",
            website="https://shell.com.br",
            opening_hours={"Mon-Fri": "06:00-22:00"},
            amenities=["banheiro", "loja"],
        )

    def test_creates_milestone_with_correct_id(self, factory, sample_poi):
        """Milestone should have POI ID."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert milestone.id == "poi_123"

    def test_creates_milestone_with_correct_name(self, factory, sample_poi):
        """Milestone should have POI name."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert milestone.name == "Posto Shell"

    def test_creates_milestone_with_correct_type(self, factory, sample_poi):
        """Milestone should have correct type from category."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert milestone.type == MilestoneType.GAS_STATION

    def test_creates_milestone_with_coordinates(self, factory, sample_poi):
        """Milestone should have POI coordinates."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert milestone.coordinates.latitude == -23.5505
        assert milestone.coordinates.longitude == -46.6333

    def test_creates_milestone_with_distance(self, factory, sample_poi):
        """Milestone should have distance from origin."""
        milestone = factory.create_from_poi(
            sample_poi, 15.5, (-23.55, -46.63)
        )
        assert milestone.distance_from_origin_km == 15.5

    def test_creates_milestone_with_phone(self, factory, sample_poi):
        """Milestone should have phone from POI."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert milestone.phone == "+55 11 1234-5678"

    def test_creates_milestone_with_website(self, factory, sample_poi):
        """Milestone should have website from POI."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert milestone.website == "https://shell.com.br"

    def test_creates_milestone_with_quality_score(self, factory, sample_poi):
        """Milestone should have quality score from provider data."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert milestone.quality_score == 0.8

    def test_creates_milestone_with_amenities(self, factory, sample_poi):
        """Milestone should have amenities from POI."""
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63)
        )
        assert "banheiro" in milestone.amenities
        assert "loja" in milestone.amenities

    def test_nearby_poi_no_detour(self, factory, sample_poi):
        """POI close to route should not require detour."""
        # POI at route point - 0 distance
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.5505, -46.6333)
        )
        assert milestone.requires_detour is False

    def test_distant_poi_requires_detour(self, factory):
        """POI far from route should require detour."""
        # POI 1km from route point
        poi = POI(
            id="poi_distant",
            name="Distant POI",
            category=POICategory.RESTAURANT,
            location=GeoLocation(latitude=-23.56, longitude=-46.64),  # Far from route
            provider_data={},
        )
        milestone = factory.create_from_poi(
            poi, 10.0, (-23.55, -46.63)  # Route point
        )
        # Distance > 500m should require detour
        assert milestone.requires_detour is True

    def test_city_poi_type(self, factory):
        """POI with place=city should have CITY type."""
        poi = POI(
            id="city_1",
            name="Sao Paulo",
            category=POICategory.SERVICES,
            location=GeoLocation(latitude=-23.55, longitude=-46.63),
            provider_data={"osm_tags": {"place": "city"}},
        )
        milestone = factory.create_from_poi(poi, 10.0, (-23.55, -46.63))
        assert milestone.type == MilestoneType.CITY

    def test_town_poi_type(self, factory):
        """POI with place=town should have TOWN type."""
        poi = POI(
            id="town_1",
            name="Small Town",
            category=POICategory.SERVICES,
            location=GeoLocation(latitude=-23.55, longitude=-46.63),
            provider_data={"osm_tags": {"place": "town"}},
        )
        milestone = factory.create_from_poi(poi, 10.0, (-23.55, -46.63))
        assert milestone.type == MilestoneType.TOWN

    def test_village_poi_type(self, factory):
        """POI with place=village should have VILLAGE type."""
        poi = POI(
            id="village_1",
            name="Village",
            category=POICategory.SERVICES,
            location=GeoLocation(latitude=-23.55, longitude=-46.63),
            provider_data={"osm_tags": {"place": "village"}},
        )
        milestone = factory.create_from_poi(poi, 10.0, (-23.55, -46.63))
        assert milestone.type == MilestoneType.VILLAGE

    def test_with_junction_info(self, factory, sample_poi):
        """Should handle junction info for distant POIs."""
        junction_info = (12.5, (-23.56, -46.64), 0.8, "right")
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63), junction_info
        )
        assert milestone.junction_distance_km == 12.5
        assert milestone.junction_coordinates is not None
        assert milestone.junction_coordinates.latitude == -23.56
        assert milestone.side == "right"

    def test_junction_close_to_poi_no_detour(self, factory, sample_poi):
        """Junction very close to POI should not require detour."""
        # access_route_distance_km < 0.1
        junction_info = (12.5, (-23.56, -46.64), 0.05, "left")
        milestone = factory.create_from_poi(
            sample_poi, 10.0, (-23.55, -46.63), junction_info
        )
        assert milestone.requires_detour is False
        assert milestone.junction_distance_km is None


class TestAssignMilestonesToSegments:
    """Tests for assigning milestones to segments."""

    @pytest.fixture
    def factory(self):
        """Create factory instance."""
        return MilestoneFactory()

    @pytest.fixture
    def sample_segments(self):
        """Create sample segments."""
        return [
            LinearRoadSegment(
                id="seg_1",
                name="BR-116",
                start_distance_km=0.0,
                end_distance_km=10.0,
                length_km=10.0,
                start_coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                end_coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                milestones=[],
            ),
            LinearRoadSegment(
                id="seg_2",
                name="BR-116",
                start_distance_km=10.0,
                end_distance_km=20.0,
                length_km=10.0,
                start_coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                end_coordinates=Coordinates(latitude=-23.65, longitude=-46.73),
                milestones=[],
            ),
        ]

    @pytest.fixture
    def sample_milestones(self):
        """Create sample milestones."""
        return [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.56, longitude=-46.64),
                distance_from_origin_km=5.0,  # In segment 1
                distance_from_road_meters=50.0,
                side="right",
            ),
            RoadMilestone(
                id="m2",
                name="POI 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.58, longitude=-46.66),
                distance_from_origin_km=8.0,  # In segment 1
                distance_from_road_meters=100.0,
                side="left",
            ),
            RoadMilestone(
                id="m3",
                name="POI 3",
                type=MilestoneType.HOTEL,
                coordinates=Coordinates(latitude=-23.62, longitude=-46.70),
                distance_from_origin_km=15.0,  # In segment 2
                distance_from_road_meters=150.0,
                side="right",
            ),
        ]

    def test_assigns_milestones_to_correct_segments(
        self, factory, sample_segments, sample_milestones
    ):
        """Milestones should be assigned to correct segments."""
        factory.assign_to_segments(sample_segments, sample_milestones)

        assert len(sample_segments[0].milestones) == 2
        assert len(sample_segments[1].milestones) == 1

    def test_milestones_sorted_by_distance(
        self, factory, sample_segments, sample_milestones
    ):
        """Milestones in each segment should be sorted by distance."""
        factory.assign_to_segments(sample_segments, sample_milestones)

        segment_1_distances = [
            m.distance_from_origin_km for m in sample_segments[0].milestones
        ]
        assert segment_1_distances == sorted(segment_1_distances)

    def test_milestone_at_segment_boundary(self, factory, sample_segments):
        """Milestone at segment boundary should be included."""
        milestones = [
            RoadMilestone(
                id="m1",
                name="Boundary POI",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                distance_from_origin_km=10.0,  # At boundary
                distance_from_road_meters=50.0,
                side="right",
            ),
        ]
        factory.assign_to_segments(sample_segments, milestones)

        # Should be in first segment (end_distance_km is inclusive)
        assert len(sample_segments[0].milestones) == 1

    def test_empty_milestones_list(self, factory, sample_segments):
        """Empty milestones list should result in empty segment milestones."""
        factory.assign_to_segments(sample_segments, [])

        assert sample_segments[0].milestones == []
        assert sample_segments[1].milestones == []

    def test_module_function_works(self, sample_segments, sample_milestones):
        """Module-level function should work."""
        assign_milestones_to_segments(sample_segments, sample_milestones)

        assert len(sample_segments[0].milestones) == 2
        assert len(sample_segments[1].milestones) == 1


class TestMilestoneFactoryEnrichWithCities:
    """Tests for city enrichment."""

    @pytest.fixture
    def factory_with_provider(self):
        """Create factory with mock geo provider."""
        mock_provider = MagicMock()
        mock_provider.reverse_geocode = AsyncMock()
        return MilestoneFactory(geo_provider=mock_provider)

    @pytest.fixture
    def sample_milestones(self):
        """Create milestones without cities."""
        return [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                city=None,
            ),
            RoadMilestone(
                id="m2",
                name="POI 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.56, longitude=-46.64),
                distance_from_origin_km=15.0,
                distance_from_road_meters=100.0,
                side="left",
                city="Existing City",  # Already has city
            ),
        ]

    @pytest.mark.asyncio
    async def test_enriches_milestones_without_city(
        self, factory_with_provider, sample_milestones
    ):
        """Should only geocode milestones without city."""
        factory_with_provider.geo_provider.reverse_geocode.return_value = GeoLocation(
            latitude=-23.55, longitude=-46.63, city="Sao Paulo"
        )

        await factory_with_provider.enrich_with_cities(sample_milestones)

        # Should only call for milestone without city
        assert factory_with_provider.geo_provider.reverse_geocode.call_count == 1
        assert sample_milestones[0].city == "Sao Paulo"
        assert sample_milestones[1].city == "Existing City"

    @pytest.mark.asyncio
    async def test_handles_geocoding_failure(
        self, factory_with_provider, sample_milestones
    ):
        """Should handle geocoding failures gracefully."""
        factory_with_provider.geo_provider.reverse_geocode.side_effect = Exception("API error")

        # Should not raise
        await factory_with_provider.enrich_with_cities(sample_milestones)

        # City should still be None
        assert sample_milestones[0].city is None

    @pytest.mark.asyncio
    async def test_no_provider_logs_warning(self, sample_milestones):
        """Should warn if no provider configured."""
        factory = MilestoneFactory(geo_provider=None)

        # Should not raise
        await factory.enrich_with_cities(sample_milestones)
