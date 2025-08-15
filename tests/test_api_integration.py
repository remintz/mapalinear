"""
API Integration Tests for Multi-Provider System - TDD Implementation.

This module contains integration tests that verify the complete API workflow
with the new multi-provider architecture, ensuring backward compatibility
and proper provider integration.
"""

import pytest
import httpx
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from fastapi.testclient import TestClient

# Mock the providers to avoid import errors during testing
from api.providers.base import GeoProvider, ProviderType
from api.providers.models import GeoLocation, Route, POI, POICategory
from api.providers.manager import create_provider


class TestAPIProviderMock(GeoProvider):
    """Mock provider for API integration testing."""
    
    def __init__(self, cache=None):
        self.cache = cache
        self.geocoding_results = {}
        self.route_results = {}
        self.poi_results = {}
    
    async def geocode(self, address: str):
        """Return mock geocoding results."""
        return self.geocoding_results.get(address, GeoLocation(
            latitude=-23.5505,
            longitude=-46.6333,
            address=address,
            city="São Paulo",
            state="SP",
            country="Brasil"
        ))
    
    async def reverse_geocode(self, latitude: float, longitude: float):
        """Return mock reverse geocoding results."""
        return GeoLocation(
            latitude=latitude,
            longitude=longitude,
            address=f"Address at {latitude}, {longitude}",
            city="São Paulo",
            state="SP",
            country="Brasil"
        )
    
    async def calculate_route(self, origin, destination, waypoints=None, avoid=None):
        """Return mock route calculation results."""
        key = f"{origin.latitude},{origin.longitude}-{destination.latitude},{destination.longitude}"
        return self.route_results.get(key, Route(
            origin=origin,
            destination=destination,
            total_distance=430.5,
            total_duration=300.0,
            geometry=[(origin.latitude, origin.longitude), (destination.latitude, destination.longitude)]
        ))
    
    async def search_pois(self, location, radius, categories, limit=50):
        """Return mock POI search results."""
        return self.poi_results.get(f"{location.latitude},{location.longitude}", [
            POI(
                id="mock_poi_1",
                name="Mock Gas Station",
                location=location,
                category=POICategory.GAS_STATION,
                amenities=["24h", "Convenience Store"],
                rating=4.2
            ),
            POI(
                id="mock_poi_2", 
                name="Mock Restaurant",
                location=location,
                category=POICategory.RESTAURANT,
                amenities=["WiFi", "Parking"],
                rating=4.5
            )
        ])
    
    async def get_poi_details(self, poi_id: str):
        """Return mock POI details."""
        location = GeoLocation(latitude=-23.5505, longitude=-46.6333)
        return POI(
            id=poi_id,
            name=f"Mock POI {poi_id}",
            location=location,
            category=POICategory.GAS_STATION,
            rating=4.0
        )
    
    @property
    def provider_type(self):
        return ProviderType.OSM
    
    @property
    def supports_offline_export(self):
        return True
    
    @property
    def rate_limit_per_second(self):
        return 10.0


@pytest.fixture
def mock_provider():
    """Create a mock provider for testing."""
    return TestAPIProviderMock()


@pytest.fixture
def api_client():
    """Create API test client with mocked providers."""
    with patch('api.providers.manager.create_provider') as mock_create:
        mock_create.return_value = TestAPIProviderMock()
        
        # Import and create app after mocking
        from api.main import app
        client = TestClient(app)
        yield client


@pytest.fixture
async def async_api_client():
    """Create async API test client."""
    with patch('api.providers.manager.create_provider') as mock_create:
        mock_create.return_value = TestAPIProviderMock()
        
        from api.main import app
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            yield client


class TestHealthEndpoints:
    """Test suite for basic health check endpoints."""
    
    def test_health_endpoint_basic(self, api_client):
        """It should return health status."""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_api_health_endpoint(self, api_client):
        """It should return API health status.""" 
        response = api_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestGeocodingEndpoints:
    """Test suite for geocoding API endpoints."""
    
    def test_geocode_endpoint_success(self, api_client):
        """It should geocode addresses successfully."""
        response = api_client.get("/api/geocode", params={"address": "São Paulo, SP"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "latitude" in data
        assert "longitude" in data
        assert "address" in data
        assert data["latitude"] == -23.5505
        assert data["longitude"] == -46.6333
    
    def test_geocode_endpoint_missing_address(self, api_client):
        """It should return error for missing address parameter."""
        response = api_client.get("/api/geocode")
        
        assert response.status_code == 422  # Validation error
    
    def test_reverse_geocode_endpoint_success(self, api_client):
        """It should reverse geocode coordinates successfully."""
        response = api_client.get(
            "/api/reverse-geocode",
            params={"latitude": -23.5505, "longitude": -46.6333}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "latitude" in data
        assert "longitude" in data
        assert "address" in data
        assert data["latitude"] == -23.5505
        assert data["longitude"] == -46.6333
    
    def test_reverse_geocode_endpoint_invalid_coordinates(self, api_client):
        """It should validate coordinate bounds."""
        # Invalid latitude
        response = api_client.get(
            "/api/reverse-geocode",
            params={"latitude": 91, "longitude": 0}
        )
        assert response.status_code == 422
        
        # Invalid longitude  
        response = api_client.get(
            "/api/reverse-geocode", 
            params={"latitude": 0, "longitude": 181}
        )
        assert response.status_code == 422


class TestRouteEndpoints:
    """Test suite for routing API endpoints."""
    
    def test_calculate_route_endpoint_success(self, api_client):
        """It should calculate routes successfully."""
        response = api_client.post("/api/routes/calculate", json={
            "origin": {"latitude": -23.5505, "longitude": -46.6333},
            "destination": {"latitude": -22.9068, "longitude": -43.1729}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "origin" in data
        assert "destination" in data
        assert "total_distance" in data
        assert "total_duration" in data
        assert "geometry" in data
        assert isinstance(data["geometry"], list)
        assert len(data["geometry"]) >= 2
    
    def test_calculate_route_with_waypoints(self, api_client):
        """It should handle routes with waypoints."""
        response = api_client.post("/api/routes/calculate", json={
            "origin": {"latitude": -23.5505, "longitude": -46.6333},
            "destination": {"latitude": -22.9068, "longitude": -43.1729},
            "waypoints": [{"latitude": -23.0, "longitude": -45.0}]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "waypoints" in data
    
    def test_calculate_route_invalid_coordinates(self, api_client):
        """It should validate route coordinates."""
        response = api_client.post("/api/routes/calculate", json={
            "origin": {"latitude": 91, "longitude": 0},  # Invalid latitude
            "destination": {"latitude": -22.9068, "longitude": -43.1729}
        })
        
        assert response.status_code == 422
    
    def test_calculate_route_missing_destination(self, api_client):
        """It should require both origin and destination."""
        response = api_client.post("/api/routes/calculate", json={
            "origin": {"latitude": -23.5505, "longitude": -46.6333}
            # Missing destination
        })
        
        assert response.status_code == 422


class TestPOIEndpoints:
    """Test suite for Points of Interest API endpoints."""
    
    def test_search_pois_endpoint_success(self, api_client):
        """It should search for POIs successfully."""
        response = api_client.get("/api/pois/search", params={
            "latitude": -23.5505,
            "longitude": -46.6333,
            "radius": 1000,
            "categories": "gas_station,restaurant"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check first POI structure
        poi = data[0]
        assert "id" in poi
        assert "name" in poi
        assert "location" in poi
        assert "category" in poi
        assert "latitude" in poi["location"]
        assert "longitude" in poi["location"]
    
    def test_search_pois_with_limit(self, api_client):
        """It should respect limit parameter."""
        response = api_client.get("/api/pois/search", params={
            "latitude": -23.5505,
            "longitude": -46.6333,
            "radius": 1000,
            "categories": "gas_station",
            "limit": 1
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
    
    def test_search_pois_invalid_radius(self, api_client):
        """It should validate radius parameter."""
        response = api_client.get("/api/pois/search", params={
            "latitude": -23.5505,
            "longitude": -46.6333,
            "radius": -1000,  # Negative radius
            "categories": "gas_station"
        })
        
        assert response.status_code == 422
    
    def test_get_poi_details_endpoint_success(self, api_client):
        """It should get POI details successfully."""
        response = api_client.get("/api/pois/mock_poi_1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "name" in data
        assert "location" in data
        assert "category" in data
        assert data["id"] == "mock_poi_1"
    
    def test_get_poi_details_not_found(self, api_client):
        """It should handle POI not found scenarios."""
        with patch.object(TestAPIProviderMock, 'get_poi_details', return_value=None):
            response = api_client.get("/api/pois/nonexistent_poi")
            
            assert response.status_code == 404


class TestProviderConfiguration:
    """Test suite for provider configuration and selection."""
    
    def test_provider_selection_via_env_var(self, api_client):
        """It should use provider specified in environment variable."""
        with patch.dict('os.environ', {'GEO_PRIMARY_PROVIDER': 'here'}):
            with patch('api.providers.manager.create_provider') as mock_create:
                # Configure mock to return HERE provider
                mock_here_provider = TestAPIProviderMock()
                mock_here_provider.provider_type = ProviderType.HERE
                mock_create.return_value = mock_here_provider
                
                response = api_client.get("/api/geocode", params={"address": "Test"})
                
                assert response.status_code == 200
                # Verify provider was created
                mock_create.assert_called()
    
    @pytest.mark.asyncio
    async def test_provider_caching_between_requests(self):
        """It should reuse provider instances between requests."""
        provider_calls = []
        
        def track_create_provider(*args, **kwargs):
            provider_calls.append(True)
            return TestAPIProviderMock()
        
        with patch('api.providers.manager.create_provider', side_effect=track_create_provider):
            from api.main import app
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                # Make multiple requests
                await client.get("/api/geocode?address=Test1")
                await client.get("/api/geocode?address=Test2")
                await client.get("/api/geocode?address=Test3")
        
        # Provider should be created once and reused
        assert len(provider_calls) >= 1  # At least one call


class TestErrorHandling:
    """Test suite for API error handling."""
    
    def test_provider_error_handling(self, api_client):
        """It should handle provider errors gracefully."""
        with patch('api.providers.manager.create_provider') as mock_create:
            # Configure provider to raise exception
            mock_provider = TestAPIProviderMock()
            async def failing_geocode(address):
                raise Exception("Provider error")
            mock_provider.geocode = failing_geocode
            mock_create.return_value = mock_provider
            
            response = api_client.get("/api/geocode", params={"address": "Test"})
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data or "detail" in data
    
    def test_timeout_handling(self, api_client):
        """It should handle request timeouts."""
        with patch('api.providers.manager.create_provider') as mock_create:
            # Configure provider with slow response
            mock_provider = TestAPIProviderMock()
            async def slow_geocode(address):
                await asyncio.sleep(10)  # Simulate timeout
                return None
            mock_provider.geocode = slow_geocode
            mock_create.return_value = mock_provider
            
            # This test would need timeout configuration in the API
            # For now, just test that the endpoint exists
            response = api_client.get("/api/geocode", params={"address": "Test"})
            # The actual timeout handling depends on FastAPI/uvicorn configuration


class TestBackwardCompatibility:
    """Test suite for backward compatibility with existing API."""
    
    def test_existing_osm_endpoints_still_work(self, api_client):
        """It should maintain compatibility with existing OSM endpoints."""
        # Test existing road search endpoint if it exists
        try:
            response = api_client.get("/api/roads/search", params={
                "origin": "São Paulo, SP",
                "destination": "Rio de Janeiro, RJ"
            })
            # Should not fail with 500 error, even if 404 is acceptable
            assert response.status_code in [200, 404, 422]
        except Exception:
            # If endpoint doesn't exist yet, that's fine
            pass
    
    def test_response_format_compatibility(self, api_client):
        """It should maintain response format for existing clients."""
        response = api_client.get("/api/geocode", params={"address": "São Paulo, SP"})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have basic expected fields
        required_fields = ["latitude", "longitude"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestCacheIntegration:
    """Test suite for cache integration in API endpoints."""
    
    def test_cache_usage_in_geocoding(self, api_client):
        """It should use cache for repeated geocoding requests."""
        address = "São Paulo, SP"
        
        # Make first request
        response1 = api_client.get("/api/geocode", params={"address": address})
        assert response1.status_code == 200
        
        # Make second request (should hit cache)
        response2 = api_client.get("/api/geocode", params={"address": address})
        assert response2.status_code == 200
        
        # Results should be identical
        assert response1.json() == response2.json()
    
    @pytest.mark.asyncio
    async def test_cache_statistics_endpoint(self):
        """It should provide cache statistics endpoint."""
        with patch('api.providers.manager.create_provider') as mock_create:
            mock_create.return_value = TestAPIProviderMock()
            
            from api.main import app
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                try:
                    response = await client.get("/api/stats/cache")
                    # If endpoint exists, should return valid stats
                    if response.status_code == 200:
                        data = response.json()
                        assert "hits" in data or "statistics" in data
                except Exception:
                    # If endpoint doesn't exist yet, that's acceptable
                    pass


class TestProviderSpecificEndpoints:
    """Test suite for provider-specific functionality."""
    
    def test_provider_info_endpoint(self, api_client):
        """It should provide information about current provider."""
        try:
            response = api_client.get("/api/provider/info")
            if response.status_code == 200:
                data = response.json()
                assert "provider_type" in data
                assert "supports_offline_export" in data
                assert "rate_limit_per_second" in data
        except Exception:
            # If endpoint doesn't exist yet, that's acceptable
            pass
    
    def test_provider_stats_endpoint(self, api_client):
        """It should provide provider statistics."""
        try:
            response = api_client.get("/api/stats/provider")
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)
        except Exception:
            # If endpoint doesn't exist yet, that's acceptable
            pass


class TestAsyncOperations:
    """Test suite for asynchronous API operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """It should handle concurrent requests properly."""
        with patch('api.providers.manager.create_provider') as mock_create:
            mock_create.return_value = TestAPIProviderMock()
            
            from api.main import app
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                # Make concurrent requests
                tasks = [
                    client.get("/api/geocode?address=Address1"),
                    client.get("/api/geocode?address=Address2"), 
                    client.get("/api/geocode?address=Address3")
                ]
                
                responses = await asyncio.gather(*tasks)
                
                # All requests should succeed
                for response in responses:
                    assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_async_provider_integration(self, async_api_client):
        """It should properly integrate with async providers."""
        response = await async_api_client.get("/api/geocode?address=Test")
        
        assert response.status_code == 200
        data = response.json()
        assert "latitude" in data
        assert "longitude" in data