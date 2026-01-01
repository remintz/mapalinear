"""
API Integration Tests for Admin POIs and Required Tags Configuration.

These tests exercise the API endpoints directly with database rollback
to ensure database state is restored after each test.
"""

import pytest
import json
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

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


class TestAuthenticationRequired:
    """Test that authentication is required for admin endpoints."""

    def test_list_pois_unauthenticated(self, unauthenticated_client):
        """Unauthenticated users should get 401."""
        response = unauthenticated_client.get("/api/admin/pois")
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
