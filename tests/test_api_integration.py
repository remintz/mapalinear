"""
API Integration Tests for Simplified API Structure.

This module contains integration tests that verify the simplified API endpoints
after the major refactoring that removed unused endpoints.

Only tests the essential endpoints that are actually used by the frontend:
- GET /health - Health check
- POST /api/operations/linear-map - Start async route search
- GET /api/operations/{operation_id} - Operation status
- POST /api/export/geojson - Export as GeoJSON
- POST /api/export/gpx - Export as GPX
- POST /api/export/web-urls - URLs for web tools
"""

import pytest
import httpx
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime

# Mock the providers to avoid import errors during testing
from api.providers.base import GeoProvider, ProviderType
from api.providers.models import GeoLocation, Route, POI, POICategory
from api.providers.manager import create_provider


def create_mock_user():
    """Create a mock user for authentication."""
    user = Mock()
    user.id = uuid4()
    user.google_id = "test_google_123"
    user.email = "test@example.com"
    user.name = "Test User"
    user.avatar_url = None
    user.is_active = True
    user.is_admin = False
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    user.last_login_at = datetime.now()
    return user


class APIProviderMock(GeoProvider):
    """Mock provider for API integration testing."""

    def __init__(self, cache=None):
        self.cache = cache
        self.geocoding_results = {}
        self.route_results = {}
        self.poi_results = {}

    async def geocode(self, address: str):
        """Return mock geocoding results."""
        return self.geocoding_results.get(
            address,
            GeoLocation(
                latitude=-23.5505,
                longitude=-46.6333,
                address=address,
                city="São Paulo",
                state="SP",
                country="Brasil",
            ),
        )

    async def reverse_geocode(self, latitude: float, longitude: float):
        """Return mock reverse geocoding results."""
        return GeoLocation(
            latitude=latitude,
            longitude=longitude,
            address=f"Address at {latitude}, {longitude}",
            city="São Paulo",
            state="SP",
            country="Brasil",
        )

    async def calculate_route(
        self, origin: GeoLocation, destination: GeoLocation, waypoints=None, avoid=None
    ):
        """Return mock route results."""
        return Route(
            origin=origin,
            destination=destination,
            waypoints=waypoints or [],
            distance_km=400.0,
            duration_minutes=300,
            geometry="mock_geometry_string",
            bbox=(-46.7, -23.7, -46.5, -23.3),
        )

    async def search_pois(
        self, location: GeoLocation, radius: float, categories: list, limit: int = 100
    ):
        """Return mock POI results."""
        return [
            POI(
                id="mock_poi_1",
                name="Mock Gas Station",
                category=POICategory.gas_station,
                location=GeoLocation(
                    latitude=location.latitude + 0.01,
                    longitude=location.longitude + 0.01,
                    address="Mock address",
                    city="São Paulo",
                    state="SP",
                    country="Brasil",
                ),
                distance_km=1.0,
                tags={"amenity": "fuel"},
            )
        ]

    async def get_poi_details(self, poi_id: str):
        """Return mock POI details."""
        if poi_id == "mock_poi_1":
            return POI(
                id=poi_id,
                name="Mock Gas Station",
                category=POICategory.gas_station,
                location=GeoLocation(
                    latitude=-23.5505,
                    longitude=-46.6333,
                    address="Mock address",
                    city="São Paulo",
                    state="SP",
                    country="Brasil",
                ),
                distance_km=0.0,
                tags={"amenity": "fuel"},
            )
        return None

    @property
    def provider_type(self) -> ProviderType:
        """Return the provider type identifier."""
        return ProviderType.OSM

    @property
    def supports_offline_export(self) -> bool:
        """Whether this provider's data can be exported for offline use."""
        return True

    @property
    def rate_limit_per_second(self) -> float:
        """Maximum requests per second for this provider."""
        return 1.0


@pytest.fixture
def mock_provider():
    """Create a mock provider for testing."""
    return APIProviderMock()


@pytest.fixture
def api_client(mock_provider):
    """Create a test client for the API with mocked authentication."""
    from api.models.road_models import AsyncOperationResponse, OperationStatus
    from api.middleware.auth import get_current_user
    from api.main import app
    import uuid

    # Store created operations for get_operation to retrieve
    created_operations = {}

    async def mock_create_operation(operation_type: str):
        op_id = str(uuid.uuid4())
        response = AsyncOperationResponse(
            operation_id=op_id,
            type=operation_type,
            status=OperationStatus.IN_PROGRESS,
            started_at=datetime.now(),
            progress_percent=0.0,
        )
        created_operations[op_id] = response
        return response

    async def mock_get_operation(operation_id: str):
        return created_operations.get(operation_id)

    def mock_run_async(operation_id: str, function, *args, **kwargs):
        pass  # Do nothing - prevents background DB access

    # Create mock user for authentication
    mock_user = create_mock_user()

    # Override the authentication dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch("api.providers.manager.create_provider", return_value=mock_provider), \
         patch("api.services.async_service.AsyncService.create_operation", side_effect=mock_create_operation), \
         patch("api.services.async_service.AsyncService.get_operation", side_effect=mock_get_operation), \
         patch("api.services.async_service.AsyncService.run_async", side_effect=mock_run_async):

        with TestClient(app) as client:
            yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


# Removed - replaced with inline async client in tests


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint_basic(self, api_client):
        """It should return health status."""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestLinearMapOperations:
    """Test the main linear map operations endpoints."""

    def test_start_linear_map_operation(self, api_client):
        """It should start a linear map operation successfully."""
        request_data = {
            "origin": "São Paulo, SP",
            "destination": "Rio de Janeiro, RJ",
            "road_id": None,
            "include_cities": True,
            "include_gas_stations": True,
            "include_food": True,
            "include_toll_booths": True,
            "max_distance_from_road": 5.0,
            "min_distance_from_origin_km": 0.0,
        }

        response = api_client.post("/api/operations/linear-map", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "operation_id" in data
        assert "status" in data
        assert data["status"] == "in_progress"

    def test_start_linear_map_missing_required_fields(self, api_client):
        """It should return error for missing required fields."""
        request_data = {
            "origin": "São Paulo, SP",
            # Missing destination
        }

        response = api_client.post("/api/operations/linear-map", json=request_data)

        assert response.status_code == 422

    def test_get_operation_status(self, api_client):
        """It should return operation status."""
        # First start an operation
        request_data = {
            "origin": "São Paulo, SP",
            "destination": "Rio de Janeiro, RJ",
            "road_id": None,
            "include_cities": True,
            "include_gas_stations": True,
            "include_food": True,
            "include_toll_booths": True,
            "max_distance_from_road": 5.0,
            "min_distance_from_origin_km": 0.0,
        }

        start_response = api_client.post(
            "/api/operations/linear-map", json=request_data
        )
        assert start_response.status_code == 200
        operation_id = start_response.json()["operation_id"]

        # Then check its status
        status_response = api_client.get(f"/api/operations/{operation_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert "operation_id" in data
        assert "status" in data
        assert data["operation_id"] == operation_id

    def test_get_nonexistent_operation(self, api_client):
        """It should return 404 for nonexistent operation."""
        response = api_client.get("/api/operations/nonexistent_operation_id")

        assert response.status_code == 404


class TestExportEndpoints:
    """Test export functionality endpoints."""

    def test_export_geojson_success(self, api_client):
        """It should export data as GeoJSON successfully."""
        # Mock data structure that matches ExportRouteData
        export_data = {
            "origin": "São Paulo, SP",
            "destination": "Rio de Janeiro, RJ",
            "total_distance_km": 400.0,
            "segments": [],
            "pois": [
                {
                    "id": "poi_1",
                    "name": "Test Gas Station",
                    "type": "gas_station",
                    "coordinates": {"lat": -23.0, "lon": -45.0},
                    "distance_from_origin_km": 100.0,
                }
            ],
        }

        response = api_client.post("/api/export/geojson", json=export_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_export_gpx_success(self, api_client):
        """It should export data as GPX successfully."""
        export_data = {
            "origin": "São Paulo, SP",
            "destination": "Rio de Janeiro, RJ",
            "total_distance_km": 400.0,
            "segments": [],
            "pois": [
                {
                    "id": "poi_1",
                    "name": "Test Gas Station",
                    "type": "gas_station",
                    "coordinates": {"lat": -23.0, "lon": -45.0},
                    "distance_from_origin_km": 100.0,
                }
            ],
        }

        response = api_client.post("/api/export/gpx", json=export_data)

        assert response.status_code == 200
        # GPX should return XML content
        assert "xml" in response.headers.get("content-type", "").lower()
        # Should have proper Content-Disposition header with sanitized filename
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition
        assert "filename" in content_disposition
        # Filename should not contain non-ASCII characters
        assert "rota_Sao_Paulo_SP_Rio_de_Janeiro_RJ.gpx" in content_disposition
        # GPX should return some form of file response - just check that it doesn't error
        # Note: The actual content might be binary/XML, so we don't assert on content-type
        # GPX should return some form of file response - just check that it doesn't error
        # Note: The actual content might be binary/XML, so we don't assert on content-type

    def test_export_web_urls_success(self, api_client):
        """It should return web visualization URLs successfully."""
        export_data = {
            "origin": "São Paulo, SP",
            "destination": "Rio de Janeiro, RJ",
            "total_distance_km": 400.0,
            "segments": [],
            "pois": [
                {
                    "id": "poi_1",
                    "name": "Test Gas Station",
                    "type": "gas_station",
                    "coordinates": {"lat": -23.0, "lon": -45.0},
                    "distance_from_origin_km": 100.0,
                }
            ],
        }

        response = api_client.post("/api/export/web-urls", json=export_data)

        assert response.status_code == 200
        data = response.json()
        # The endpoint returns multiple URL fields, not a nested "urls" object
        assert (
            "osrm_map_url" in data or "overpass_turbo_url" in data or "umap_url" in data
        )


class TestErrorHandling:
    """Test error handling across the API."""

    def test_invalid_json_request(self, api_client):
        """It should handle invalid JSON gracefully."""
        response = api_client.post(
            "/api/operations/linear-map",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_nonexistent_endpoint(self, api_client):
        """It should return 404 for nonexistent endpoints."""
        response = api_client.get("/api/nonexistent/endpoint")

        assert response.status_code == 404


class TestAsyncOperations:
    """Test asynchronous operation behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_provider):
        """It should handle multiple concurrent operations."""
        from api.models.road_models import AsyncOperationResponse, OperationStatus
        from api.middleware.auth import get_current_user
        from api.main import app
        import uuid

        # Create a mock for AsyncService.create_operation that returns unique operation IDs
        async def mock_create_operation(operation_type: str):
            return AsyncOperationResponse(
                operation_id=str(uuid.uuid4()),
                type=operation_type,
                status=OperationStatus.IN_PROGRESS,
                started_at=datetime.now(),
                progress_percent=0.0,
            )

        # Mock run_async to prevent background tasks from actually running
        def mock_run_async(operation_id: str, function, *args, **kwargs):
            pass  # Do nothing - prevents background DB access

        # Create mock user for authentication
        mock_user = create_mock_user()

        # Override the authentication dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("api.providers.manager.create_provider", return_value=mock_provider), \
             patch("api.routers.operations_router.AsyncService.create_operation", side_effect=mock_create_operation), \
             patch("api.routers.operations_router.AsyncService.run_async", side_effect=mock_run_async):

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                request_data = {
                    "origin": "São Paulo, SP",
                    "destination": "Rio de Janeiro, RJ",
                    "road_id": None,
                    "include_cities": True,
                    "include_gas_stations": True,
                    "include_food": True,
                    "include_toll_booths": True,
                    "max_distance_from_road": 5.0,
                    "min_distance_from_origin_km": 0.0,
                }

                # Start multiple operations concurrently
                tasks = [
                    client.post("/api/operations/linear-map", json=request_data)
                    for _ in range(3)
                ]

                responses = await asyncio.gather(*tasks)

                # All requests should succeed
                for response in responses:
                    assert response.status_code == 200
                    data = response.json()
                    assert "operation_id" in data
                    assert "status" in data

        # Clean up dependency overrides
        app.dependency_overrides.clear()


class TestBackwardCompatibility:
    """Test that essential functionality still works."""

    def test_root_endpoint(self, api_client):
        """It should return welcome message."""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Bem-vindo" in data["message"]
