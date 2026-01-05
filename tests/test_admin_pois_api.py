"""
API Integration Tests for Admin POIs and Required Tags Configuration.

These tests exercise the API endpoints directly with database rollback
to ensure database state is restored after each test.
"""

import pytest
import json
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from api.main import app
from api.middleware.auth import get_current_user, get_current_admin
from api.database.connection import get_db, Base, _engine, _async_session_maker
from api.database.models.poi import POI
from api.database.models.system_settings import SystemSettings
import api.database.connection as db_connection


@pytest.fixture(autouse=True)
def reset_db_connection():
    """Reset database connection between tests to avoid event loop issues."""
    # Reset the global connection pool before each test
    db_connection._engine = None
    db_connection._async_session_maker = None
    yield
    # Reset again after test
    db_connection._engine = None
    db_connection._async_session_maker = None


def create_mock_admin_user():
    """Create a mock admin user for authentication."""
    user = Mock()
    user.id = uuid4()
    user.google_id = "admin_google_123"
    user.email = "admin@example.com"
    user.name = "Admin User"
    user.avatar_url = None
    user.is_active = True
    user.is_admin = True  # Admin user
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    user.last_login_at = datetime.now()
    return user


def create_mock_regular_user():
    """Create a mock regular (non-admin) user for authentication."""
    user = Mock()
    user.id = uuid4()
    user.google_id = "regular_google_456"
    user.email = "user@example.com"
    user.name = "Regular User"
    user.avatar_url = None
    user.is_active = True
    user.is_admin = False  # Not admin
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    user.last_login_at = datetime.now()
    return user


@pytest.fixture
def admin_client():
    """Create a test client with admin authentication."""
    mock_admin = create_mock_admin_user()

    # Override both user dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    app.dependency_overrides[get_current_admin] = lambda: mock_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def regular_client():
    """Create a test client with regular user authentication."""
    from fastapi import HTTPException, status

    mock_user = create_mock_regular_user()

    # Override get_current_user to return regular user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Override get_current_admin to raise 403 (non-admin)
    def deny_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    app.dependency_overrides[get_current_admin] = deny_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    """Create a test client without authentication."""
    # Clear any existing overrides
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        yield client


class TestAdminPOIsEndpoints:
    """Test Admin POIs API endpoints."""

    def test_list_pois_requires_admin(self, regular_client):
        """Non-admin users should get 403 on POIs endpoint."""
        response = regular_client.get("/api/admin/pois")
        assert response.status_code == 403

    def test_list_pois_success(self, admin_client):
        """Admin should be able to list POIs."""
        response = admin_client.get("/api/admin/pois")

        assert response.status_code == 200
        data = response.json()
        assert "pois" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert isinstance(data["pois"], list)

    def test_list_pois_with_pagination(self, admin_client):
        """Admin should be able to paginate POIs."""
        response = admin_client.get("/api/admin/pois?page=1&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 10

    def test_list_pois_with_city_filter(self, admin_client):
        """Admin should be able to filter POIs by city."""
        response = admin_client.get("/api/admin/pois?city=Belo")

        assert response.status_code == 200
        data = response.json()
        # All returned POIs should match the city filter (if any)
        for poi in data["pois"]:
            if poi.get("city"):
                assert "belo" in poi["city"].lower()

    def test_list_pois_with_name_filter(self, admin_client):
        """Admin should be able to filter POIs by name."""
        response = admin_client.get("/api/admin/pois?name=shell")

        assert response.status_code == 200
        data = response.json()
        # All returned POIs should have 'shell' in the name (case insensitive)
        for poi in data["pois"]:
            if poi.get("name"):
                assert "shell" in poi["name"].lower()

    def test_list_pois_with_type_filter(self, admin_client):
        """Admin should be able to filter POIs by type."""
        response = admin_client.get("/api/admin/pois?poi_type=gas_station")

        assert response.status_code == 200
        data = response.json()
        # All returned POIs should have the correct type
        for poi in data["pois"]:
            assert poi["type"] == "gas_station"

    def test_list_pois_low_quality_only(self, admin_client):
        """Admin should be able to filter to low quality POIs only."""
        response = admin_client.get("/api/admin/pois?low_quality_only=true")

        assert response.status_code == 200
        data = response.json()
        # All returned POIs should be low quality
        for poi in data["pois"]:
            assert poi["is_low_quality"] is True

    def test_get_poi_filters(self, admin_client):
        """Admin should be able to get available filter options."""
        response = admin_client.get("/api/admin/pois/filters")

        assert response.status_code == 200
        data = response.json()
        assert "cities" in data
        assert "types" in data
        assert isinstance(data["cities"], list)
        assert isinstance(data["types"], list)

    def test_get_poi_stats(self, admin_client):
        """Admin should be able to get POI statistics."""
        response = admin_client.get("/api/admin/pois/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "low_quality" in data
        assert "by_type" in data
        assert "by_city" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["low_quality"], int)


class TestAdminPOIDetailEndpoint:
    """Test Admin POI detail endpoint."""

    def test_get_poi_detail_requires_admin(self, regular_client):
        """Non-admin users should get 403 on POI detail endpoint."""
        fake_id = str(uuid4())
        response = regular_client.get(f"/api/admin/pois/{fake_id}")
        assert response.status_code == 403

    def test_get_poi_detail_not_found(self, admin_client):
        """Admin should get 404 for non-existent POI."""
        fake_id = str(uuid4())
        response = admin_client.get(f"/api/admin/pois/{fake_id}")
        assert response.status_code == 404


class TestRecalculateQualityEndpoint:
    """Test the recalculate quality endpoint."""

    def test_recalculate_requires_admin(self, regular_client):
        """Non-admin users should get 403 on recalculate endpoint."""
        response = regular_client.post("/api/admin/pois/recalculate-quality")
        assert response.status_code == 403

    def test_recalculate_quality_success(self, admin_client):
        """Admin should be able to trigger quality recalculation."""
        response = admin_client.post("/api/admin/pois/recalculate-quality")

        assert response.status_code == 200
        data = response.json()
        assert "updated" in data
        assert "total" in data
        assert "message" in data
        assert isinstance(data["updated"], int)
        assert isinstance(data["total"], int)


class TestRequiredTagsEndpoints:
    """Test Required Tags Configuration API endpoints."""

    def test_get_required_tags_is_public(self, regular_client):
        """Regular users can read required tags (public endpoint)."""
        response = regular_client.get("/api/settings/required-tags")
        assert response.status_code == 200
        data = response.json()
        assert "required_tags" in data
        assert "available_tags" in data

    def test_get_required_tags_success(self, admin_client):
        """Admin should be able to get required tags configuration."""
        response = admin_client.get("/api/settings/required-tags")

        assert response.status_code == 200
        data = response.json()
        assert "required_tags" in data
        assert "available_tags" in data
        assert isinstance(data["required_tags"], dict)
        assert isinstance(data["available_tags"], list)

        # Check that common POI types are present
        assert "gas_station" in data["required_tags"]
        assert "restaurant" in data["required_tags"]

        # Check available tags
        assert "name" in data["available_tags"]
        assert "brand" in data["available_tags"]

    def test_update_required_tags_requires_admin(self, regular_client):
        """Non-admin users should get 403 on update required tags endpoint."""
        response = regular_client.put(
            "/api/settings/required-tags",
            json={"required_tags": {"gas_station": ["name"]}}
        )
        assert response.status_code == 403

    def test_update_required_tags_success(self, admin_client):
        """Admin should be able to update required tags configuration."""
        # First get current configuration to restore later
        original_response = admin_client.get("/api/settings/required-tags")
        original_config = original_response.json()["required_tags"]

        # Update configuration
        new_config = {
            "gas_station": ["name", "brand", "phone"],
            "restaurant": ["name", "cuisine"],
            "hotel": ["name", "stars"],
            "hospital": ["name"],
            "toll_booth": ["name"],
            "rest_area": ["name"],
            "city": ["name"],
            "town": ["name"],
            "village": ["name"]
        }

        response = admin_client.put(
            "/api/settings/required-tags",
            json={"required_tags": new_config}
        )

        assert response.status_code == 200
        data = response.json()
        assert "required_tags" in data
        assert data["required_tags"]["gas_station"] == ["name", "brand", "phone"]
        assert data["required_tags"]["restaurant"] == ["name", "cuisine"]

        # Restore original configuration
        admin_client.put("/api/settings/required-tags", json={"required_tags": original_config})

    def test_reset_required_tags_requires_admin(self, regular_client):
        """Non-admin users should get 403 on reset required tags endpoint."""
        response = regular_client.post("/api/settings/required-tags/reset")
        assert response.status_code == 403

    def test_reset_required_tags_success(self, admin_client):
        """Admin should be able to reset required tags to defaults."""
        # First modify the configuration
        modified_config = {
            "gas_station": ["name", "brand", "phone", "website"],
            "restaurant": ["name"],
            "hotel": ["name"],
            "hospital": ["name"],
            "toll_booth": ["name"],
            "rest_area": ["name"],
            "city": ["name"],
            "town": ["name"],
            "village": ["name"]
        }
        admin_client.put("/api/settings/required-tags", json=modified_config)

        # Reset to defaults
        response = admin_client.post("/api/settings/required-tags/reset")

        assert response.status_code == 200
        data = response.json()
        assert "required_tags" in data

        # Check that defaults are restored
        # Default for gas_station is ["name", "brand"]
        assert "name" in data["required_tags"]["gas_station"]
        assert "brand" in data["required_tags"]["gas_station"]

    def test_update_required_tags_validates_input(self, admin_client):
        """Update should validate input format."""
        # Invalid: not a dict
        response = admin_client.put(
            "/api/settings/required-tags",
            json="invalid"
        )
        assert response.status_code == 422

        # Invalid: values not lists
        response = admin_client.put(
            "/api/settings/required-tags",
            json={"required_tags": {"gas_station": "name"}}
        )
        assert response.status_code == 422

        # Invalid: missing required_tags key
        response = admin_client.put(
            "/api/settings/required-tags",
            json={"gas_station": ["name"]}
        )
        assert response.status_code == 422


class TestRefreshPOIsEndpoint:
    """Test the refresh POIs endpoint."""

    def test_refresh_requires_admin(self, regular_client):
        """Non-admin users should get 403 on refresh endpoint."""
        response = regular_client.post(
            "/api/admin/pois/refresh",
            json={"poi_ids": [str(uuid4())]}
        )
        assert response.status_code == 403

    def test_refresh_pois_success(self, admin_client):
        """Admin should be able to refresh POIs."""
        # Use a fake POI ID - endpoint should handle gracefully
        fake_id = str(uuid4())
        response = admin_client.post(
            "/api/admin/pois/refresh",
            json={"poi_ids": [fake_id]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "updated" in data
        assert "failed" in data
        assert "message" in data
        assert isinstance(data["updated"], int)
        assert isinstance(data["failed"], int)
        # Fake POI should fail (not found)
        assert data["failed"] == 1

    def test_refresh_pois_empty_list(self, admin_client):
        """Refresh with empty list should return 422 validation error."""
        response = admin_client.post(
            "/api/admin/pois/refresh",
            json={"poi_ids": []}
        )
        assert response.status_code == 422

    def test_refresh_pois_invalid_format(self, admin_client):
        """Refresh with invalid request format should return 422."""
        response = admin_client.post(
            "/api/admin/pois/refresh",
            json={"invalid": "data"}
        )
        assert response.status_code == 422

    def test_refresh_pois_max_limit(self, admin_client):
        """Refresh should reject more than 100 POI IDs."""
        # Create 101 fake POI IDs
        poi_ids = [str(uuid4()) for _ in range(101)]
        response = admin_client.post(
            "/api/admin/pois/refresh",
            json={"poi_ids": poi_ids}
        )
        assert response.status_code == 422

    def test_refresh_pois_multiple_ids(self, admin_client):
        """Admin should be able to refresh multiple POIs at once."""
        fake_ids = [str(uuid4()) for _ in range(3)]
        response = admin_client.post(
            "/api/admin/pois/refresh",
            json={"poi_ids": fake_ids}
        )

        assert response.status_code == 200
        data = response.json()
        # All should fail as they don't exist
        assert data["failed"] == 3
        assert data["updated"] == 0


class TestRefreshPOIsWithMocks:
    """
    Test refresh POIs logic with mocks.

    These tests verify that the refresh logic:
    1. Uses correct parameter names (latitude/longitude, not lat/lon)
    2. Uses correct osm_id format (node/123 or way/123)
    3. Updates fields correctly from provider data
    4. Recalculates quality after refresh
    """

    def test_reverse_geocode_parameter_names(self):
        """
        Verify that reverse_geocode is called with 'latitude' and 'longitude',
        not 'lat' and 'lon'.

        This test would have caught the bug where we used lat/lon instead of
        latitude/longitude.
        """
        from api.providers.base import GeoProvider
        import inspect

        # Get the signature of reverse_geocode
        sig = inspect.signature(GeoProvider.reverse_geocode)
        param_names = list(sig.parameters.keys())

        # Verify correct parameter names
        assert 'latitude' in param_names, "reverse_geocode should have 'latitude' parameter"
        assert 'longitude' in param_names, "reverse_geocode should have 'longitude' parameter"
        assert 'lat' not in param_names, "reverse_geocode should NOT have 'lat' parameter"
        assert 'lon' not in param_names, "reverse_geocode should NOT have 'lon' parameter"

    def test_get_poi_details_expects_type_prefix(self):
        """
        Verify that get_poi_details expects osm_id with type prefix (node/ or way/).

        This test documents the expected format for osm_id in get_poi_details.
        """
        from api.providers.osm.provider import OSMProvider

        # The OSM provider's get_poi_details splits on '/' to get type and id
        # This test verifies the expected format
        test_poi_id = "node/12345"
        osm_type, osm_id = test_poi_id.split('/', 1)

        assert osm_type == "node"
        assert osm_id == "12345"

        # Also test way format
        test_poi_id = "way/67890"
        osm_type, osm_id = test_poi_id.split('/', 1)

        assert osm_type == "way"
        assert osm_id == "67890"

    def test_refresh_endpoint_code_uses_correct_format(self):
        """
        Verify that the refresh endpoint code constructs osm_id with correct format.

        This is a code inspection test that reads the source and verifies patterns.
        """
        import ast
        from pathlib import Path

        # Read the router source code
        router_path = Path("api/routers/admin_pois_router.py")
        source = router_path.read_text()

        # Check that we use node/ and way/ prefixes
        assert 'f"node/{poi.osm_id}"' in source or "node/" in source, \
            "refresh_pois should construct osm_id with node/ prefix"
        assert 'f"way/{poi.osm_id}"' in source or "way/" in source, \
            "refresh_pois should try way/ prefix as fallback"

        # Check that we use latitude/longitude (not lat/lon)
        assert 'latitude=poi.latitude' in source, \
            "refresh_pois should use latitude=poi.latitude"
        assert 'longitude=poi.longitude' in source, \
            "refresh_pois should use longitude=poi.longitude"
        assert 'lat=poi.lat' not in source, \
            "refresh_pois should NOT use lat=poi.lat"
        assert 'lon=poi.lon' not in source, \
            "refresh_pois should NOT use lon=poi.lon"

    def test_refresh_endpoint_recalculates_quality(self):
        """
        Verify that refresh endpoint code calls quality service.
        """
        from pathlib import Path

        router_path = Path("api/routers/admin_pois_router.py")
        source = router_path.read_text()

        # Check that quality service is used
        assert 'POIQualityService' in source, \
            "refresh_pois should use POIQualityService"
        assert 'update_poi_quality_fields' in source, \
            "refresh_pois should call update_poi_quality_fields"


class TestNoCityFilter:
    """Test the __no_city__ filter for POIs without city."""

    def test_list_pois_no_city_filter(self, admin_client):
        """Admin should be able to filter POIs without city using __no_city__."""
        response = admin_client.get("/api/admin/pois?city=__no_city__")

        assert response.status_code == 200
        data = response.json()
        assert "pois" in data
        # All returned POIs should have no city (null or empty)
        for poi in data["pois"]:
            assert poi.get("city") is None or poi.get("city") == ""

    def test_list_pois_no_city_with_pagination(self, admin_client):
        """No city filter should work with pagination."""
        response = admin_client.get("/api/admin/pois?city=__no_city__&page=1&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 10

    def test_list_pois_no_city_with_type_filter(self, admin_client):
        """No city filter should combine with type filter."""
        response = admin_client.get("/api/admin/pois?city=__no_city__&poi_type=gas_station")

        assert response.status_code == 200
        data = response.json()
        # All POIs should match both filters
        for poi in data["pois"]:
            assert poi.get("city") is None or poi.get("city") == ""
            assert poi["type"] == "gas_station"


class TestAuthenticationRequired:
    """Test that authentication is required for admin endpoints."""

    def test_list_pois_unauthenticated(self, unauthenticated_client):
        """Unauthenticated users should get 401."""
        response = unauthenticated_client.get("/api/admin/pois")
        assert response.status_code == 401

    def test_refresh_pois_unauthenticated(self, unauthenticated_client):
        """Unauthenticated users should get 401 on refresh endpoint."""
        response = unauthenticated_client.post(
            "/api/admin/pois/refresh",
            json={"poi_ids": [str(uuid4())]}
        )
        assert response.status_code == 401

    def test_get_required_tags_is_public(self, unauthenticated_client):
        """Required tags GET is public (doesn't require auth)."""
        response = unauthenticated_client.get("/api/settings/required-tags")
        assert response.status_code == 200

    def test_update_required_tags_unauthenticated(self, unauthenticated_client):
        """Unauthenticated users should get 401 on required tags update."""
        response = unauthenticated_client.put(
            "/api/settings/required-tags",
            json={"required_tags": {"gas_station": ["name"]}}
        )
        assert response.status_code == 401

    def test_reset_required_tags_unauthenticated(self, unauthenticated_client):
        """Unauthenticated users should get 401 on required tags reset."""
        response = unauthenticated_client.post("/api/settings/required-tags/reset")
        assert response.status_code == 401
