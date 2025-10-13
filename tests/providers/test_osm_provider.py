"""
Tests for OSM Provider implementation - TDD Implementation.

This module contains comprehensive tests for the OSM provider,
verifying that it correctly implements the GeoProvider interface
and maintains compatibility with the existing OSM functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Optional

from api.providers.osm.provider import OSMProvider
from api.providers.base import ProviderType
from api.providers.models import GeoLocation, Route, POI, POICategory
from api.providers.cache import UnifiedCache


class TestOSMProviderBasics:
    """Test basic functionality of OSM Provider."""
    
    @pytest.fixture
    def osm_provider(self, clean_cache):
        """Create OSM provider with clean cache."""
        return OSMProvider(cache=clean_cache)
    
    def test_provider_type_identification(self, osm_provider):
        """It should identify itself as OSM provider."""
        assert osm_provider.provider_type == ProviderType.OSM
    
    def test_offline_export_support(self, osm_provider):
        """It should support offline data export."""
        assert osm_provider.supports_offline_export == True
    
    def test_rate_limiting_configuration(self, osm_provider):
        """It should have appropriate rate limiting for OSM APIs."""
        assert osm_provider.rate_limit_per_second == 1.0


class TestOSMProviderGeocoding:
    """Test geocoding functionality of OSM Provider."""
    
    @pytest.fixture
    def osm_provider(self, clean_cache):
        """Create OSM provider with clean cache."""
        return OSMProvider(cache=clean_cache)
    
    @pytest.mark.asyncio
    async def test_geocode_basic_functionality(self, osm_provider):
        """It should geocode addresses using Nominatim API."""
        # Create a mock location object
        from unittest.mock import Mock
        mock_location = Mock()
        mock_location.latitude = -23.5505
        mock_location.longitude = -46.6333
        mock_location.address = "São Paulo, SP, Brasil"
        
        with patch.object(osm_provider.geolocator, 'geocode') as mock_geocode:
            mock_geocode.return_value = mock_location
            
            result = await osm_provider.geocode("São Paulo, SP")
            
            assert result is not None
            assert result.latitude == -23.5505
            assert result.longitude == -46.6333
            assert result.address == "São Paulo, SP, Brasil"
            assert result.country == "Brasil"
    
    @pytest.mark.asyncio
    async def test_geocode_not_found(self, osm_provider):
        """It should return None for addresses that cannot be geocoded."""
        with patch.object(osm_provider.geolocator, 'geocode') as mock_geocode:
            mock_geocode.return_value = None
            
            result = await osm_provider.geocode("NonexistentPlace, XX")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_reverse_geocode_functionality(self, osm_provider):
        """It should reverse geocode coordinates to addresses."""
        # Create mock location for reverse geocoding
        from unittest.mock import Mock
        mock_location = Mock()
        mock_location.address = "Centro, São Paulo, SP, Brasil"
        
        with patch.object(osm_provider.geolocator, 'reverse') as mock_reverse:
            mock_reverse.return_value = mock_location
            
            result = await osm_provider.reverse_geocode(-23.5505, -46.6333)
            
            assert result is not None
            assert result.latitude == -23.5505
            assert result.longitude == -46.6333
            assert result.address == "Centro, São Paulo, SP, Brasil"
    
    @pytest.mark.asyncio
    async def test_geocode_caches_results(self, osm_provider):
        """It should cache geocoding results to improve performance."""
        from unittest.mock import Mock
        mock_location = Mock()
        mock_location.latitude = -23.5505
        mock_location.longitude = -46.6333
        mock_location.address = "São Paulo, SP, Brasil"
        
        with patch.object(osm_provider.geolocator, 'geocode') as mock_geocode:
            mock_geocode.return_value = mock_location
            
            # First call
            result1 = await osm_provider.geocode("São Paulo, SP")
            # Second call (should use cache if available)
            result2 = await osm_provider.geocode("São Paulo, SP")
            
            assert result1 is not None
            assert result2 is not None
            assert result1.latitude == result2.latitude
            assert result1.longitude == result2.longitude


class TestOSMProviderRouting:
    """Test routing functionality of OSM Provider."""
    
    @pytest.fixture
    def osm_provider(self, clean_cache):
        """Create OSM provider with clean cache."""
        return OSMProvider(cache=clean_cache)
    
    @pytest.mark.asyncio
    async def test_calculate_route_basic(self, osm_provider, sample_locations):
        """It should calculate routes between two points."""
        origin = sample_locations['sao_paulo']
        destination = sample_locations['rio_janeiro']
        
        # Mock the routing calculation
        mock_route_data = {
            'distance': 430500,  # meters
            'duration': 18000,   # seconds (5 hours)
            'geometry': [
                (-23.5505, -46.6333),
                (-23.0000, -45.0000),
                (-22.9068, -43.1729)
            ]
        }
        
        with patch.object(osm_provider, '_calculate_osm_route') as mock_route:
            mock_route.return_value = mock_route_data
            
            result = await osm_provider.calculate_route(origin, destination)
            
            assert result is not None
            assert result.origin == origin
            assert result.destination == destination
            assert result.total_distance == 430.5  # km
            assert result.total_duration == 300.0   # minutes
            assert len(result.geometry) == 3
    
    @pytest.mark.asyncio 
    async def test_calculate_route_with_waypoints(self, osm_provider, sample_locations):
        """It should calculate routes with intermediate waypoints."""
        origin = sample_locations['sao_paulo']
        destination = sample_locations['rio_janeiro']
        waypoints = [sample_locations['belo_horizonte']]
        
        with patch.object(osm_provider, '_calculate_osm_route') as mock_route:
            mock_route.return_value = {
                'distance': 500000, 
                'duration': 20000, 
                'geometry': [(-23.5505, -46.6333), (-22.9068, -43.1729)]
            }
            
            result = await osm_provider.calculate_route(origin, destination, waypoints)
            
            assert result is not None
            assert result.waypoints == waypoints
    
    @pytest.mark.asyncio
    async def test_calculate_route_avoids_features(self, osm_provider, sample_locations):
        """It should respect avoid parameters when calculating routes."""
        origin = sample_locations['sao_paulo']  
        destination = sample_locations['rio_janeiro']
        avoid = ['tolls', 'highways']
        
        with patch.object(osm_provider, '_calculate_osm_route') as mock_route:
            mock_route.return_value = {
                'distance': 480000, 
                'duration': 22000, 
                'geometry': [(-23.5505, -46.6333), (-22.9068, -43.1729)]
            }
            
            result = await osm_provider.calculate_route(origin, destination, avoid=avoid)
            
            assert result is not None
            # Should call with avoid parameters - check call was made
            mock_route.assert_called_once()
            # Verify the avoid parameter was passed (checking positional args)
            call_args = mock_route.call_args[0]  # positional arguments
            assert len(call_args) >= 4  # origin, destination, waypoints, avoid


class TestOSMProviderPOISearch:
    """Test POI search functionality of OSM Provider."""
    
    @pytest.fixture
    def osm_provider(self, clean_cache):
        """Create OSM provider with clean cache."""
        return OSMProvider(cache=clean_cache)
    
    @pytest.mark.asyncio
    async def test_search_pois_basic(self, osm_provider, sample_locations):
        """It should search for POIs around a location."""
        location = sample_locations['sao_paulo']
        categories = [POICategory.GAS_STATION, POICategory.RESTAURANT]
        
        # Mock Overpass API response
        mock_overpass_data = {
            'elements': [
                {
                    'type': 'node',
                    'id': 123456,
                    'lat': -23.5505,
                    'lon': -46.6333,
                    'tags': {
                        'amenity': 'fuel',
                        'brand': 'Shell',
                        'name': 'Posto Shell Centro'
                    }
                },
                {
                    'type': 'node',
                    'id': 123457,
                    'lat': -23.5510,
                    'lon': -46.6330,
                    'tags': {
                        'amenity': 'restaurant',
                        'cuisine': 'brazilian',
                        'name': 'Restaurante Família',
                        'phone': '+55 11 1234-5678',
                        'opening_hours': 'Mo-Su 11:00-23:00'
                    }
                }
            ]
        }
        
        with patch.object(osm_provider, '_make_overpass_request') as mock_overpass:
            mock_overpass.return_value = mock_overpass_data
            
            results = await osm_provider.search_pois(location, 1000, categories, limit=10)
            
            assert len(results) == 2
            
            # Check gas station POI
            gas_station = next((poi for poi in results if poi.category == POICategory.GAS_STATION), None)
            assert gas_station is not None
            assert gas_station.name == "Posto Shell Centro"
            
            # Check restaurant POI
            restaurant = next((poi for poi in results if poi.category == POICategory.RESTAURANT), None)
            assert restaurant is not None
            assert restaurant.name == "Restaurante Família"
    
    @pytest.mark.asyncio
    async def test_search_pois_respects_limit(self, osm_provider, sample_locations):
        """It should respect the limit parameter in POI searches."""
        location = sample_locations['sao_paulo']
        categories = [POICategory.GAS_STATION]
        
        # Mock response with more POIs than limit
        mock_elements = []
        for i in range(20):  # Create 20 POIs
            mock_elements.append({
                'type': 'node',
                'id': 123456 + i,
                'lat': -23.5505 + (i * 0.001),
                'lon': -46.6333,
                'tags': {
                    'amenity': 'fuel',
                    'name': f'Posto {i+1}'
                }
            })
        
        mock_overpass_data = {'elements': mock_elements}
        
        with patch.object(osm_provider, '_make_overpass_request') as mock_overpass:
            mock_overpass.return_value = mock_overpass_data
            
            results = await osm_provider.search_pois(location, 1000, categories, limit=5)
            
            assert len(results) <= 5
    
    @pytest.mark.asyncio
    async def test_get_poi_details(self, osm_provider):
        """It should get detailed information about a specific POI."""
        poi_id = "node/123456"
        
        mock_overpass_data = {
            'elements': [{
                'type': 'node',
                'id': 123456,
                'lat': -23.5505,
                'lon': -46.6333,
                'tags': {
                    'amenity': 'fuel',
                    'brand': 'Shell',
                    'name': 'Posto Shell Centro',
                    'opening_hours': '24/7',
                    'phone': '+55 11 1234-5678',
                    'website': 'https://shell.com.br'
                }
            }]
        }
        
        with patch.object(osm_provider, '_make_overpass_request') as mock_overpass:
            mock_overpass.return_value = mock_overpass_data
            
            result = await osm_provider.get_poi_details(poi_id)
            
            assert result is not None
            assert result.name == "Posto Shell Centro"
            assert result.phone == "+55 11 1234-5678"
            assert result.website == "https://shell.com.br"


class TestOSMProviderIntegration:
    """Integration tests for OSM Provider with the original OSMService."""
    
    @pytest.fixture
    def osm_provider(self, clean_cache):
        """Create OSM provider with clean cache."""
        return OSMProvider(cache=clean_cache)
    
    @pytest.mark.asyncio
    async def test_maintains_compatibility_with_existing_cache(self, osm_provider):
        """It should maintain compatibility with existing cache structure."""
        # This test ensures that the refactored provider can work with
        # data that was cached by the original OSMService
        pass  # Implementation depends on actual cache migration strategy
    
    @pytest.mark.asyncio
    async def test_error_handling_matches_original(self, osm_provider):
        """It should handle errors in the same way as the original OSMService."""
        with patch.object(osm_provider.geolocator, 'geocode') as mock_geocode:
            # Simulate network error
            mock_geocode.side_effect = Exception("Network error")
            
            result = await osm_provider.geocode("Test Address")
            assert result is None  # Should handle errors gracefully
    
    def test_rate_limiting_configuration_matches_original(self, osm_provider):
        """It should use the same rate limiting as the original OSMService."""
        assert osm_provider.rate_limit_per_second == 1.0
        assert hasattr(osm_provider, '_last_request_time')
        assert hasattr(osm_provider, '_query_delay')


class TestOSMProviderInternalMethods:
    """Test internal helper methods of OSM Provider."""
    
    @pytest.fixture
    def osm_provider(self, clean_cache):
        """Create OSM provider with clean cache."""
        return OSMProvider(cache=clean_cache)
    
    def test_normalize_poi_category_mapping(self, osm_provider):
        """It should correctly map OSM amenity tags to POI categories."""
        assert osm_provider._map_osm_amenity_to_category('fuel') == POICategory.GAS_STATION
        assert osm_provider._map_osm_amenity_to_category('restaurant') == POICategory.RESTAURANT
        assert osm_provider._map_osm_amenity_to_category('hotel') == POICategory.HOTEL
        assert osm_provider._map_osm_amenity_to_category('hospital') == POICategory.HOSPITAL
        assert osm_provider._map_osm_amenity_to_category('pharmacy') == POICategory.PHARMACY
    
    def test_generate_overpass_query(self, osm_provider):
        """It should generate correct Overpass queries for POI search."""
        location = GeoLocation(latitude=-23.5505, longitude=-46.6333)
        categories = [POICategory.GAS_STATION, POICategory.RESTAURANT]
        
        query = osm_provider._generate_overpass_query(location, 1000, categories)
        
        assert '[out:json]' in query
        assert '"amenity"="fuel"' in query
        assert '"amenity"="restaurant"' in query
        assert 'out meta;' in query
    
    def test_parse_osm_element_to_poi(self, osm_provider):
        """It should correctly parse OSM elements to POI objects."""
        osm_element = {
            'type': 'node',
            'id': 123456,
            'lat': -23.5505,
            'lon': -46.6333,
            'tags': {
                'amenity': 'fuel',
                'brand': 'Shell',
                'name': 'Posto Shell Centro',
                'opening_hours': '24/7'
            }
        }

        poi = osm_provider._parse_osm_element_to_poi(osm_element)

        assert poi.id == "node/123456"
        assert poi.name == "Posto Shell Centro"
        assert poi.category == POICategory.GAS_STATION
        assert poi.location.latitude == -23.5505
        assert poi.location.longitude == -46.6333
        # Check for the new format '24h' instead of 'Horário: 24/7'
        assert '24h' in poi.amenities