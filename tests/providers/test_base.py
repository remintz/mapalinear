"""
Tests for base provider interfaces and models - TDD Implementation.

This module contains comprehensive tests for the core provider interfaces
and unified models, following Test-Driven Development principles.
"""

import pytest
from typing import List, Optional
from pydantic import ValidationError

from api.providers.base import ProviderType, GeoProvider
from api.providers.models import (
    GeoLocation, Route, RouteSegment, POI, POICategory, ProviderStats
)


class TestProviderType:
    """Test suite for ProviderType enumeration."""
    
    def test_provider_type_values(self):
        """It should have correct string values for each provider type."""
        assert ProviderType.OSM.value == "osm"
        assert ProviderType.HERE.value == "here"
        assert ProviderType.TOMTOM.value == "tomtom"
    
    def test_provider_type_from_string(self):
        """It should create ProviderType from string values."""
        assert ProviderType("osm") == ProviderType.OSM
        assert ProviderType("here") == ProviderType.HERE
        assert ProviderType("tomtom") == ProviderType.TOMTOM
    
    def test_provider_type_invalid_string(self):
        """It should raise ValueError for invalid provider strings."""
        with pytest.raises(ValueError):
            ProviderType("invalid_provider")


class TestGeoLocationModel:
    """Test suite for GeoLocation unified model."""
    
    def test_basic_geolocation_creation(self, sample_locations):
        """It should create GeoLocation with valid coordinates."""
        location = sample_locations['sao_paulo']
        
        assert location.latitude == -23.5505
        assert location.longitude == -46.6333
        assert location.city == "São Paulo"
        assert location.state == "SP"
        assert location.country == "Brasil"
    
    def test_geolocation_minimal_data(self):
        """It should create GeoLocation with only coordinates."""
        location = GeoLocation(latitude=0, longitude=0)
        
        assert location.latitude == 0
        assert location.longitude == 0
        assert location.address is None
        assert location.city is None
        assert location.country == "Brasil"  # Default value
    
    def test_geolocation_immutable(self, sample_locations):
        """It should be immutable (frozen)."""
        location = sample_locations['sao_paulo']
        
        with pytest.raises(ValidationError):
            location.latitude = -25.0000  # Should fail because frozen=True
    
    def test_latitude_validation_bounds(self):
        """It should validate latitude within bounds [-90, 90]."""
        # Valid bounds
        GeoLocation(latitude=90, longitude=0)
        GeoLocation(latitude=-90, longitude=0)
        GeoLocation(latitude=0, longitude=0)
        
        # Invalid bounds
        with pytest.raises(ValidationError):
            GeoLocation(latitude=91, longitude=0)
        
        with pytest.raises(ValidationError):
            GeoLocation(latitude=-91, longitude=0)
    
    def test_longitude_validation_bounds(self):
        """It should validate longitude within bounds [-180, 180]."""
        # Valid bounds
        GeoLocation(latitude=0, longitude=180)
        GeoLocation(latitude=0, longitude=-180)
        GeoLocation(latitude=0, longitude=0)
        
        # Invalid bounds
        with pytest.raises(ValidationError):
            GeoLocation(latitude=0, longitude=181)
        
        with pytest.raises(ValidationError):
            GeoLocation(latitude=0, longitude=-181)


class TestRouteSegmentModel:
    """Test suite for RouteSegment model."""
    
    def test_route_segment_creation(self, sample_locations):
        """It should create RouteSegment with start and end locations."""
        start = sample_locations['sao_paulo']
        end = sample_locations['belo_horizonte']
        
        segment = RouteSegment(
            start_location=start,
            end_location=end,
            distance=580.2,
            duration=420.0,  # 7 hours
            road_name="BR-381",
            road_type="highway"
        )
        
        assert segment.start_location == start
        assert segment.end_location == end
        assert segment.distance == 580.2
        assert segment.duration == 420.0
        assert segment.road_name == "BR-381"
    
    def test_route_segment_midpoint_calculation(self, sample_locations):
        """It should calculate correct midpoint between start and end."""
        start = sample_locations['sao_paulo']  # -23.5505, -46.6333
        end = sample_locations['rio_janeiro']   # -22.9068, -43.1729
        
        segment = RouteSegment(
            start_location=start,
            end_location=end,
            distance=430.0,
            duration=300.0
        )
        
        midpoint = segment.midpoint
        expected_lat = (-23.5505 + -22.9068) / 2  # -23.22865
        expected_lon = (-46.6333 + -43.1729) / 2  # -44.9031
        
        assert abs(midpoint.latitude - expected_lat) < 0.0001
        assert abs(midpoint.longitude - expected_lon) < 0.0001
    
    def test_route_segment_negative_distance(self):
        """It should not allow negative distance."""
        start = GeoLocation(latitude=0, longitude=0)
        end = GeoLocation(latitude=1, longitude=1)
        
        with pytest.raises(ValidationError):
            RouteSegment(
                start_location=start,
                end_location=end,
                distance=-10.0,  # Invalid negative distance
                duration=60.0
            )
    
    def test_route_segment_negative_duration(self):
        """It should not allow negative duration."""
        start = GeoLocation(latitude=0, longitude=0)
        end = GeoLocation(latitude=1, longitude=1)
        
        with pytest.raises(ValidationError):
            RouteSegment(
                start_location=start,
                end_location=end,
                distance=100.0,
                duration=-30.0  # Invalid negative duration
            )


class TestRouteModel:
    """Test suite for Route unified model."""
    
    def test_route_creation(self, sample_route):
        """It should create Route with origin, destination and metadata."""
        route = sample_route
        
        assert route.total_distance == 430.5
        assert route.total_duration == 300.0
        assert len(route.geometry) == 3
        assert route.origin.city == "São Paulo"
        assert route.destination.city == "Rio de Janeiro"
        assert "BR-116" in route.road_names
    
    def test_route_minimum_geometry_points(self):
        """It should require at least 2 geometry points."""
        origin = GeoLocation(latitude=-23.5505, longitude=-46.6333)
        destination = GeoLocation(latitude=-22.9068, longitude=-43.1729)
        
        # Valid with 2 points
        route = Route(
            origin=origin,
            destination=destination,
            total_distance=430.0,
            total_duration=300.0,
            geometry=[(-23.5505, -46.6333), (-22.9068, -43.1729)]
        )
        assert len(route.geometry) == 2
        
        # Invalid with 1 point
        with pytest.raises(ValidationError):
            Route(
                origin=origin,
                destination=destination,
                total_distance=430.0,
                total_duration=300.0,
                geometry=[(-23.5505, -46.6333)]  # Only 1 point
            )
    
    def test_route_segments_optional(self, sample_locations):
        """It should allow empty segments list."""
        origin = sample_locations['sao_paulo']
        destination = sample_locations['rio_janeiro']
        
        route = Route(
            origin=origin,
            destination=destination,
            total_distance=430.0,
            total_duration=300.0,
            geometry=[(-23.5505, -46.6333), (-22.9068, -43.1729)]
        )
        
        assert route.segments == []
        assert route.waypoints == []
        assert route.road_names == []


class TestPOICategoryEnum:
    """Test suite for POICategory enumeration."""
    
    def test_poi_categories_values(self):
        """It should have correct values for common POI categories."""
        assert POICategory.GAS_STATION.value == "gas_station"
        assert POICategory.RESTAURANT.value == "restaurant"
        assert POICategory.HOTEL.value == "hotel"
        assert POICategory.HOSPITAL.value == "hospital"
        assert POICategory.PHARMACY.value == "pharmacy"
        assert POICategory.FOOD.value == "food"
    
    def test_poi_category_from_string(self):
        """It should create POICategory from string values."""
        assert POICategory("gas_station") == POICategory.GAS_STATION
        assert POICategory("restaurant") == POICategory.RESTAURANT
        assert POICategory("hotel") == POICategory.HOTEL


class TestPOIModel:
    """Test suite for POI unified model."""
    
    def test_poi_creation(self, sample_pois):
        """It should create POI with required fields."""
        poi = sample_pois[0]  # Gas station
        
        assert poi.id == "poi_gas_1"
        assert poi.name == "Posto Shell Centro"
        assert poi.category == POICategory.GAS_STATION
        assert poi.rating == 4.2
        assert poi.is_open == True
        assert "24h" in poi.amenities
        assert poi.phone == "+55 11 1234-5678"
    
    def test_poi_minimal_creation(self):
        """It should create POI with only required fields."""
        location = GeoLocation(latitude=-23.5505, longitude=-46.6333)
        
        poi = POI(
            id="minimal_poi",
            name="Minimal POI",
            location=location,
            category=POICategory.GAS_STATION
        )
        
        assert poi.id == "minimal_poi"
        assert poi.name == "Minimal POI"
        assert poi.category == POICategory.GAS_STATION
        assert poi.amenities == []
        assert poi.services == []
        assert poi.rating is None
        assert poi.provider_data == {}
    
    def test_poi_rating_validation(self):
        """It should validate rating within bounds [0, 5]."""
        location = GeoLocation(latitude=0, longitude=0)
        
        # Valid ratings
        poi_valid = POI(
            id="test", name="Test", location=location,
            category=POICategory.RESTAURANT, rating=4.5
        )
        assert poi_valid.rating == 4.5
        
        # Invalid ratings
        with pytest.raises(ValidationError):
            POI(
                id="test", name="Test", location=location,
                category=POICategory.RESTAURANT, rating=6.0  # > 5
            )
        
        with pytest.raises(ValidationError):
            POI(
                id="test", name="Test", location=location,
                category=POICategory.RESTAURANT, rating=-1.0  # < 0
            )
    
    def test_poi_review_count_validation(self):
        """It should validate review_count as non-negative."""
        location = GeoLocation(latitude=0, longitude=0)
        
        # Valid review count
        poi = POI(
            id="test", name="Test", location=location,
            category=POICategory.RESTAURANT, review_count=150
        )
        assert poi.review_count == 150
        
        # Invalid negative review count
        with pytest.raises(ValidationError):
            POI(
                id="test", name="Test", location=location,
                category=POICategory.RESTAURANT, review_count=-5
            )


class TestProviderStatsModel:
    """Test suite for ProviderStats model."""
    
    def test_provider_stats_creation(self):
        """It should create ProviderStats with metrics."""
        stats = ProviderStats(
            provider_type="osm",
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            cache_hits=300,
            cache_misses=700
        )
        
        assert stats.provider_type == "osm"
        assert stats.total_requests == 1000
        assert stats.successful_requests == 950
        assert stats.failed_requests == 50
    
    def test_success_rate_calculation(self):
        """It should calculate correct success rate percentage."""
        stats = ProviderStats(
            provider_type="here",
            total_requests=1000,
            successful_requests=950,
            failed_requests=50
        )
        
        assert stats.success_rate == 95.0
        
        # Test with zero requests
        stats_zero = ProviderStats(provider_type="osm")
        assert stats_zero.success_rate == 0.0
    
    def test_cache_hit_rate_calculation(self):
        """It should calculate correct cache hit rate percentage."""
        stats = ProviderStats(
            provider_type="osm",
            cache_hits=300,
            cache_misses=700
        )
        
        assert stats.cache_hit_rate == 30.0
        
        # Test with no cache attempts
        stats_no_cache = ProviderStats(provider_type="osm")
        assert stats_no_cache.cache_hit_rate == 0.0


class TestGeoProviderAbstractInterface:
    """Test suite for GeoProvider abstract interface."""
    
    def test_cannot_instantiate_abstract_provider(self):
        """It should not allow direct instantiation of abstract GeoProvider."""
        with pytest.raises(TypeError):
            GeoProvider()
    
    def test_mock_provider_implementation(self, mock_provider):
        """It should allow concrete implementation of abstract interface."""
        provider = mock_provider
        
        assert provider.provider_type == ProviderType.OSM
        assert provider.supports_offline_export == True
        assert provider.rate_limit_per_second == 10.0
        assert provider.call_count == 0
    
    @pytest.mark.asyncio
    async def test_provider_method_calls(self, mock_provider, sample_locations):
        """It should track method calls on mock provider."""
        provider = mock_provider
        initial_count = provider.call_count
        
        # Call various methods
        await provider.geocode("São Paulo, SP")
        await provider.reverse_geocode(-23.5505, -46.6333)
        await provider.search_pois(
            sample_locations['sao_paulo'], 
            1000, 
            [POICategory.GAS_STATION]
        )
        
        assert provider.call_count == initial_count + 3
    
    @pytest.mark.asyncio
    async def test_provider_configurable_results(self, mock_provider, sample_locations):
        """It should return configured results from mock provider."""
        provider = mock_provider
        test_location = sample_locations['sao_paulo']
        
        # Configure mock results
        provider.geocode_results["São Paulo, SP"] = test_location
        
        # Test configured result
        result = await provider.geocode("São Paulo, SP")
        assert result == test_location
        
        # Test unconfigured result
        result = await provider.geocode("Unknown Address")
        assert result is None