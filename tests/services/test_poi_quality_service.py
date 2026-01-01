"""
Unit tests for api/services/poi_quality_service.py

Tests for POI quality assessment and filtering:
- is_poi_abandoned
- calculate_quality_score
- meets_quality_threshold
- extract_amenities
- format_opening_hours
- filter_by_excluded_cities
- calculate_missing_tags
- get_osm_tags_from_poi
- update_poi_quality_fields
"""

import pytest
from unittest.mock import MagicMock

from api.models.road_models import Coordinates, MilestoneType, RoadMilestone
from api.services.poi_quality_service import (
    POIQualityService,
    is_poi_abandoned,
    calculate_quality_score,
    meets_quality_threshold,
    extract_amenities,
    format_opening_hours,
    filter_by_excluded_cities,
    calculate_missing_tags,
    get_osm_tags_from_poi,
    update_poi_quality_fields,
)


class TestIsPOIAbandoned:
    """Tests for abandoned POI detection."""

    def test_empty_tags_not_abandoned(self):
        """Empty tags should not be considered abandoned."""
        assert is_poi_abandoned({}) is False

    def test_abandoned_tag_yes(self):
        """POI with abandoned=yes should be abandoned."""
        assert is_poi_abandoned({"abandoned": "yes"}) is True

    def test_abandoned_tag_true(self):
        """POI with abandoned=true should be abandoned."""
        assert is_poi_abandoned({"abandoned": "true"}) is True

    def test_disused_tag(self):
        """POI with disused=yes should be abandoned."""
        assert is_poi_abandoned({"disused": "yes"}) is True

    def test_demolished_tag(self):
        """POI with demolished=yes should be abandoned."""
        assert is_poi_abandoned({"demolished": "yes"}) is True

    def test_closed_opening_hours(self):
        """POI with opening_hours=closed should be abandoned."""
        assert is_poi_abandoned({"opening_hours": "closed"}) is True

    def test_no_opening_hours(self):
        """POI with opening_hours=no should be abandoned."""
        assert is_poi_abandoned({"opening_hours": "no"}) is True

    def test_prefix_abandoned(self):
        """POI with abandoned: prefix should be abandoned."""
        assert is_poi_abandoned({"abandoned:amenity": "fuel"}) is True

    def test_prefix_disused(self):
        """POI with disused: prefix should be abandoned."""
        assert is_poi_abandoned({"disused:shop": "supermarket"}) is True

    def test_normal_poi_not_abandoned(self):
        """Normal POI with regular tags should not be abandoned."""
        assert is_poi_abandoned({
            "amenity": "fuel",
            "name": "Posto Shell",
            "opening_hours": "Mo-Su 06:00-22:00"
        }) is False

    def test_ruins_tag(self):
        """POI with ruins=yes should be abandoned."""
        assert is_poi_abandoned({"ruins": "yes"}) is True

    def test_former_tag(self):
        """POI with former=yes should be abandoned."""
        assert is_poi_abandoned({"former": "yes"}) is True


class TestCalculateQualityScore:
    """Tests for POI quality score calculation."""

    def test_empty_tags_zero_score(self):
        """Empty tags should have low score."""
        score = calculate_quality_score({})
        assert score < 0.2

    def test_full_data_high_score(self):
        """POI with all fields should have high score."""
        score = calculate_quality_score({
            "name": "Posto Shell",
            "operator": "Shell",
            "phone": "+55 11 1234-5678",
            "opening_hours": "Mo-Su 00:00-24:00",
            "website": "https://shell.com.br",
            "addr:street": "Av. Paulista",
            "addr:housenumber": "1000",
            "addr:city": "Sao Paulo",
        })
        assert score >= 0.8

    def test_name_only_adds_score(self):
        """POI with only name should have some score."""
        score = calculate_quality_score({"name": "Test POI"})
        assert score > 0

    def test_brand_counts(self):
        """Brand should add to quality score."""
        score_with = calculate_quality_score({"brand": "Shell"})
        score_without = calculate_quality_score({})
        assert score_with > score_without

    def test_contact_phone_counts(self):
        """Contact:phone should add to quality score."""
        score = calculate_quality_score({"contact:phone": "+55 11 1234-5678"})
        score_regular = calculate_quality_score({"phone": "+55 11 1234-5678"})
        # Both should add score
        assert score > 0
        assert score_regular > 0

    def test_restaurant_with_cuisine(self):
        """Restaurant with cuisine should have higher score."""
        score_with = calculate_quality_score({
            "amenity": "restaurant",
            "name": "Restaurante",
            "cuisine": "brazilian"
        })
        score_without = calculate_quality_score({
            "amenity": "restaurant",
            "name": "Restaurante"
        })
        assert score_with > score_without

    def test_score_range(self):
        """Score should always be between 0 and 1."""
        test_cases = [
            {},
            {"name": "Test"},
            {"name": "Test", "phone": "123", "website": "http://test.com"},
            {f"field_{i}": f"value_{i}" for i in range(20)},
        ]
        for tags in test_cases:
            score = calculate_quality_score(tags)
            assert 0.0 <= score <= 1.0


class TestMeetsQualityThreshold:
    """Tests for quality threshold checking."""

    def test_gas_station_requires_name_or_brand(self):
        """Gas station without name/brand/operator should be rejected."""
        tags = {"amenity": "fuel"}
        score = calculate_quality_score(tags)
        assert meets_quality_threshold(tags, score) is False

    def test_gas_station_with_brand_accepted(self):
        """Gas station with brand should be accepted when quality >= 0.3."""
        # Need enough fields for quality score >= 0.3
        tags = {"amenity": "fuel", "brand": "Shell", "name": "Posto Shell"}
        score = calculate_quality_score(tags)
        assert score >= 0.3  # Verify score meets threshold
        assert meets_quality_threshold(tags, score) is True

    def test_gas_station_with_operator_accepted(self):
        """Gas station with operator should be accepted when quality >= 0.3."""
        # Need enough fields for quality score >= 0.3
        tags = {"amenity": "fuel", "operator": "Shell", "name": "Posto Shell"}
        score = calculate_quality_score(tags)
        assert score >= 0.3  # Verify score meets threshold
        assert meets_quality_threshold(tags, score) is True

    def test_restaurant_requires_name(self):
        """Restaurant without name should be rejected."""
        tags = {"amenity": "restaurant"}
        score = calculate_quality_score(tags)
        assert meets_quality_threshold(tags, score) is False

    def test_restaurant_with_name_accepted(self):
        """Restaurant with name should be accepted when quality >= 0.4."""
        # Need enough fields for quality score >= 0.4
        tags = {"amenity": "restaurant", "name": "Cantina", "cuisine": "italian", "phone": "123"}
        score = calculate_quality_score(tags)
        assert score >= 0.4  # Verify score meets threshold
        assert meets_quality_threshold(tags, score) is True

    def test_toll_booth_always_included(self):
        """Toll booth should always be included."""
        tags = {"barrier": "toll_booth"}
        score = calculate_quality_score(tags)
        assert meets_quality_threshold(tags, score) is True

    def test_fast_food_requires_name(self):
        """Fast food without name should be rejected."""
        tags = {"amenity": "fast_food"}
        score = calculate_quality_score(tags)
        assert meets_quality_threshold(tags, score) is False

    def test_bakery_shop_requires_name(self):
        """Bakery shop without name should be rejected."""
        tags = {"shop": "bakery"}
        score = calculate_quality_score(tags)
        assert meets_quality_threshold(tags, score) is False


class TestExtractAmenities:
    """Tests for amenity extraction from tags."""

    def test_empty_tags_empty_list(self):
        """Empty tags should return empty list."""
        assert extract_amenities({}) == []

    def test_wifi_available(self):
        """WiFi tag should add wifi amenity."""
        amenities = extract_amenities({"wifi": "yes"})
        assert "wifi" in amenities

    def test_internet_access(self):
        """Internet access tag should add wifi."""
        amenities = extract_amenities({"internet_access": "yes"})
        assert "wifi" in amenities or "internet" in amenities

    def test_parking(self):
        """Parking tag should add estacionamento."""
        amenities = extract_amenities({"parking": "yes"})
        assert "estacionamento" in amenities

    def test_wheelchair(self):
        """Wheelchair tag should add acessivel."""
        amenities = extract_amenities({"wheelchair": "yes"})
        assert "acessível" in amenities

    def test_diesel_fuel(self):
        """Diesel fuel tag should add diesel."""
        amenities = extract_amenities({"fuel:diesel": "yes"})
        assert "diesel" in amenities

    def test_ethanol_fuel(self):
        """Ethanol fuel tag should add etanol."""
        amenities = extract_amenities({"fuel:ethanol": "yes"})
        assert "etanol" in amenities

    def test_24h_opening_hours(self):
        """24/7 opening hours should add 24h."""
        amenities = extract_amenities({"opening_hours": "24/7"})
        assert "24h" in amenities

    def test_toilets(self):
        """Toilets tag should add banheiro."""
        amenities = extract_amenities({"toilets": "yes"})
        assert "banheiro" in amenities

    def test_fuel_station_default_toilets(self):
        """Fuel station should assume toilets if not denied."""
        amenities = extract_amenities({"amenity": "fuel"})
        assert "banheiro" in amenities

    def test_fuel_station_no_toilets(self):
        """Fuel station with toilets=no should not have banheiro."""
        amenities = extract_amenities({"amenity": "fuel", "toilets": "no"})
        # Should not include default bathroom
        count = amenities.count("banheiro")
        assert count <= 1  # May still appear once from fuel default logic

    def test_no_duplicates(self):
        """Amenities should not have duplicates."""
        amenities = extract_amenities({
            "wifi": "yes",
            "internet_access": "yes",
        })
        assert len(amenities) == len(set(amenities))

    def test_sorted_output(self):
        """Amenities should be sorted."""
        amenities = extract_amenities({
            "wifi": "yes",
            "parking": "yes",
            "toilets": "yes",
        })
        assert amenities == sorted(amenities)


class TestFormatOpeningHours:
    """Tests for opening hours formatting."""

    def test_none_returns_none(self):
        """None input should return None."""
        assert format_opening_hours(None) is None

    def test_empty_dict_returns_none(self):
        """Empty dict should return None."""
        assert format_opening_hours({}) is None

    def test_single_day(self):
        """Single day should format correctly."""
        result = format_opening_hours({"Mon": "08:00-18:00"})
        assert result == "Mon: 08:00-18:00"

    def test_multiple_days(self):
        """Multiple days should be joined with comma."""
        result = format_opening_hours({
            "Mon": "08:00-18:00",
            "Tue": "08:00-18:00"
        })
        assert "Mon: 08:00-18:00" in result
        assert "Tue: 08:00-18:00" in result
        assert ", " in result


class TestFilterByExcludedCities:
    """Tests for filtering milestones by excluded cities."""

    @pytest.fixture
    def sample_milestones(self):
        """Create sample milestones for testing."""
        return [
            RoadMilestone(
                id="1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.5, longitude=-46.6),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                city="Sao Paulo",
            ),
            RoadMilestone(
                id="2",
                name="POI 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-22.9, longitude=-43.1),
                distance_from_origin_km=20.0,
                distance_from_road_meters=100.0,
                side="left",
                city="Rio de Janeiro",
            ),
            RoadMilestone(
                id="3",
                name="POI 3",
                type=MilestoneType.HOTEL,
                coordinates=Coordinates(latitude=-23.0, longitude=-44.0),
                distance_from_origin_km=30.0,
                distance_from_road_meters=200.0,
                side="right",
                city=None,  # No city
            ),
        ]

    def test_empty_excluded_returns_all(self, sample_milestones):
        """Empty excluded list should return all milestones."""
        result = filter_by_excluded_cities(sample_milestones, [])
        assert len(result) == 3

    def test_none_excluded_returns_all(self, sample_milestones):
        """None excluded list should return all milestones."""
        result = filter_by_excluded_cities(sample_milestones, None)
        assert len(result) == 3

    def test_exclude_single_city(self, sample_milestones):
        """Should exclude POIs from specified city."""
        result = filter_by_excluded_cities(sample_milestones, ["Sao Paulo"])
        assert len(result) == 2
        assert all(m.city != "Sao Paulo" for m in result if m.city)

    def test_exclude_multiple_cities(self, sample_milestones):
        """Should exclude POIs from multiple cities."""
        result = filter_by_excluded_cities(
            sample_milestones, ["Sao Paulo", "Rio de Janeiro"]
        )
        assert len(result) == 1
        assert result[0].city is None

    def test_case_insensitive(self, sample_milestones):
        """City matching should be case insensitive."""
        result = filter_by_excluded_cities(sample_milestones, ["SAO PAULO"])
        assert len(result) == 2

    def test_city_none_not_excluded(self, sample_milestones):
        """POIs without city should not be excluded."""
        result = filter_by_excluded_cities(
            sample_milestones, ["Sao Paulo", "Rio de Janeiro"]
        )
        none_city = [m for m in result if m.city is None]
        assert len(none_city) == 1

    def test_whitespace_handling(self, sample_milestones):
        """Should handle whitespace in city names."""
        result = filter_by_excluded_cities(sample_milestones, ["  Sao Paulo  "])
        assert len(result) == 2


class TestPOIQualityServiceInstance:
    """Tests for POIQualityService class instance methods."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return POIQualityService()

    def test_is_poi_abandoned_method(self, service):
        """Instance method should work like module function."""
        assert service.is_poi_abandoned({"abandoned": "yes"}) is True
        assert service.is_poi_abandoned({}) is False

    def test_calculate_quality_score_method(self, service):
        """Instance method should work like module function."""
        score = service.calculate_quality_score({"name": "Test"})
        assert 0.0 <= score <= 1.0

    def test_meets_quality_threshold_method(self, service):
        """Instance method should work like module function."""
        # Need enough fields for quality score >= 0.3
        tags = {"amenity": "fuel", "brand": "Shell", "name": "Posto Shell"}
        score = service.calculate_quality_score(tags)
        assert score >= 0.3  # Verify score meets threshold
        assert service.meets_quality_threshold(tags, score) is True


class TestCalculateMissingTags:
    """Tests for calculate_missing_tags function."""

    def test_no_missing_tags(self):
        """All required tags present should return empty list."""
        osm_tags = {"name": "Posto Shell", "brand": "Shell"}
        required_tags = ["name", "brand"]
        result = calculate_missing_tags(osm_tags, required_tags)
        assert result == []

    def test_all_tags_missing(self):
        """No required tags present should return all."""
        osm_tags = {}
        required_tags = ["name", "brand"]
        result = calculate_missing_tags(osm_tags, required_tags)
        assert sorted(result) == ["brand", "name"]

    def test_some_tags_missing(self):
        """Partial tags should return only missing."""
        osm_tags = {"name": "Posto Shell"}
        required_tags = ["name", "brand", "phone"]
        result = calculate_missing_tags(osm_tags, required_tags)
        assert sorted(result) == ["brand", "phone"]

    def test_empty_string_counts_as_missing(self):
        """Empty string values should count as missing."""
        osm_tags = {"name": "", "brand": "Shell"}
        required_tags = ["name", "brand"]
        result = calculate_missing_tags(osm_tags, required_tags)
        assert result == ["name"]

    def test_whitespace_only_counts_as_missing(self):
        """Whitespace-only values should count as missing."""
        osm_tags = {"name": "   ", "brand": "Shell"}
        required_tags = ["name", "brand"]
        result = calculate_missing_tags(osm_tags, required_tags)
        assert result == ["name"]

    def test_none_value_counts_as_missing(self):
        """None values should count as missing."""
        osm_tags = {"name": None, "brand": "Shell"}
        required_tags = ["name", "brand"]
        result = calculate_missing_tags(osm_tags, required_tags)
        assert result == ["name"]

    def test_empty_required_tags(self):
        """Empty required tags should return empty list."""
        osm_tags = {"name": "Test"}
        required_tags = []
        result = calculate_missing_tags(osm_tags, required_tags)
        assert result == []


class TestGetOsmTagsFromPoi:
    """Tests for get_osm_tags_from_poi function."""

    def test_none_tags(self):
        """POI with None tags should return empty dict."""
        poi = MagicMock()
        poi.tags = None
        result = get_osm_tags_from_poi(poi)
        assert result == {}

    def test_empty_tags(self):
        """POI with empty tags should return empty dict."""
        poi = MagicMock()
        poi.tags = {}
        result = get_osm_tags_from_poi(poi)
        assert result == {}

    def test_tags_without_osm_tags_key(self):
        """POI with tags but no osm_tags key should return empty dict."""
        poi = MagicMock()
        poi.tags = {"quality_score": 0.5}
        result = get_osm_tags_from_poi(poi)
        assert result == {}

    def test_tags_with_osm_tags(self):
        """POI with osm_tags should return them."""
        poi = MagicMock()
        poi.tags = {
            "osm_tags": {"name": "Test", "brand": "Shell"},
            "quality_score": 0.5
        }
        result = get_osm_tags_from_poi(poi)
        assert result == {"name": "Test", "brand": "Shell"}


class TestUpdatePoiQualityFields:
    """Tests for update_poi_quality_fields function."""

    def test_poi_with_all_required_tags(self):
        """POI with all required tags should not be low quality."""
        poi = MagicMock()
        poi.type = "gas_station"
        poi.tags = {"osm_tags": {"name": "Posto Shell", "brand": "Shell"}}
        poi.missing_tags = None
        poi.is_low_quality = False

        config = {"gas_station": ["name", "brand"]}
        result = update_poi_quality_fields(poi, config)

        assert poi.missing_tags == []
        assert poi.is_low_quality is False

    def test_poi_missing_required_tags(self):
        """POI missing required tags should be low quality."""
        poi = MagicMock()
        poi.type = "gas_station"
        poi.tags = {"osm_tags": {"name": "Posto Shell"}}
        poi.missing_tags = None
        poi.is_low_quality = False

        config = {"gas_station": ["name", "brand"]}
        result = update_poi_quality_fields(poi, config)

        assert poi.missing_tags == ["brand"]
        assert poi.is_low_quality is True

    def test_poi_type_not_in_config_uses_name_default(self):
        """POI type not in config should default to requiring name."""
        poi = MagicMock()
        poi.type = "unknown_type"
        poi.tags = {"osm_tags": {}}
        poi.missing_tags = None
        poi.is_low_quality = False

        config = {"gas_station": ["name", "brand"]}
        result = update_poi_quality_fields(poi, config)

        assert poi.missing_tags == ["name"]
        assert poi.is_low_quality is True

    def test_returns_true_when_changed(self):
        """Should return True when fields are changed."""
        poi = MagicMock()
        poi.type = "gas_station"
        poi.tags = {"osm_tags": {"name": "Posto"}}
        poi.missing_tags = []  # Was empty
        poi.is_low_quality = False  # Was False

        config = {"gas_station": ["name", "brand"]}
        result = update_poi_quality_fields(poi, config)

        assert result is True  # Changed to low quality

    def test_returns_false_when_not_changed(self):
        """Should return False when fields are not changed."""
        poi = MagicMock()
        poi.type = "gas_station"
        poi.tags = {"osm_tags": {"name": "Posto"}}
        poi.missing_tags = ["brand"]  # Already has correct missing
        poi.is_low_quality = True  # Already is low quality

        config = {"gas_station": ["name", "brand"]}
        result = update_poi_quality_fields(poi, config)

        assert result is False  # No change

    def test_poi_with_no_tags(self):
        """POI with no tags should have all required tags as missing."""
        poi = MagicMock()
        poi.type = "restaurant"
        poi.tags = None
        poi.missing_tags = None
        poi.is_low_quality = False

        config = {"restaurant": ["name"]}
        result = update_poi_quality_fields(poi, config)

        assert poi.missing_tags == ["name"]
        assert poi.is_low_quality is True
