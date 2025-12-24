"""
Tests for admin impersonation functionality (session-based).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.database.models.impersonation_session import ImpersonationSession
from api.database.models.user import User
from api.middleware.auth import AuthContext
from api.services.auth_service import VerifyResult


def create_mock_user(
    is_admin: bool = False,
    is_active: bool = True,
    user_id=None,
    email: str = "user@example.com",
    name: str = "Test User",
) -> Mock:
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = user_id or uuid4()
    user.google_id = f"google_{user.id}"
    user.email = email
    user.name = name
    user.avatar_url = None
    user.is_active = is_active
    user.is_admin = is_admin
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    user.last_login_at = datetime.now()
    return user


def create_mock_admin() -> Mock:
    """Create a mock admin user."""
    return create_mock_user(
        is_admin=True,
        email="admin@example.com",
        name="Admin User",
    )


def create_mock_target_user() -> Mock:
    """Create a mock target user for impersonation."""
    return create_mock_user(
        is_admin=False,
        email="target@example.com",
        name="Target User",
    )


def create_mock_impersonation_session(
    admin: Mock, target: Mock, is_active: bool = True
) -> Mock:
    """Create a mock impersonation session."""
    session = Mock(spec=ImpersonationSession)
    session.id = uuid4()
    session.admin_id = admin.id
    session.target_user_id = target.id
    session.admin = admin
    session.target_user = target
    session.is_active = is_active
    session.created_at = datetime.now(timezone.utc)
    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return session


class TestVerifyResult:
    """Test VerifyResult dataclass."""

    def test_verify_result_only_contains_user(self):
        """Test VerifyResult only contains user (no impersonation fields)."""
        user = create_mock_user()
        result = VerifyResult(user=user)

        assert result.user == user
        # VerifyResult no longer has impersonation fields
        assert not hasattr(result, "is_impersonating")
        assert not hasattr(result, "original_admin_id")


class TestAuthContext:
    """Test AuthContext dataclass."""

    def test_auth_context_default_values(self):
        """Test AuthContext has correct default values."""
        user = create_mock_user()
        context = AuthContext(user=user)

        assert context.user == user
        assert context.is_impersonating is False
        assert context.real_admin is None
        assert context.impersonation_session_id is None

    def test_auth_context_with_impersonation(self):
        """Test AuthContext with impersonation info."""
        admin = create_mock_admin()
        target = create_mock_target_user()
        session_id = str(uuid4())

        context = AuthContext(
            user=target,
            is_impersonating=True,
            real_admin=admin,
            impersonation_session_id=session_id,
        )

        assert context.user == target
        assert context.is_impersonating is True
        assert context.real_admin == admin
        assert context.impersonation_session_id == session_id


class TestImpersonationSessionRepository:
    """Test ImpersonationSessionRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = Mock()
        return session

    @pytest.mark.asyncio
    async def test_create_session(self, mock_session):
        """Test creating an impersonation session."""
        from api.database.repositories.impersonation_session import (
            ImpersonationSessionRepository,
        )

        admin = create_mock_admin()
        target = create_mock_target_user()

        # Mock the deactivate_sessions_for_admin method
        mock_session.execute.return_value = Mock(rowcount=0)

        repo = ImpersonationSessionRepository(mock_session)

        # Patch the flush and refresh to properly populate the session
        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_session.refresh = mock_refresh

        session = await repo.create_session(
            admin_id=admin.id,
            target_user_id=target.id,
        )

        assert session.admin_id == admin.id
        assert session.target_user_id == target.id
        assert session.is_active is True
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_session(self, mock_session):
        """Test deactivating an impersonation session."""
        from api.database.repositories.impersonation_session import (
            ImpersonationSessionRepository,
        )

        admin = create_mock_admin()
        target = create_mock_target_user()
        imp_session = create_mock_impersonation_session(admin, target)

        repo = ImpersonationSessionRepository(mock_session)

        # Mock get_by_id to return the session
        with patch.object(repo, "get_by_id", return_value=imp_session):
            result = await repo.deactivate_session(imp_session.id)

        assert result == imp_session
        assert imp_session.is_active is False


class TestImpersonationEndpoints:
    """Test impersonation API endpoints."""

    @pytest.fixture
    def admin_user(self):
        """Create an admin user for testing."""
        return create_mock_admin()

    @pytest.fixture
    def target_user(self):
        """Create a target user for testing."""
        return create_mock_target_user()

    @pytest.fixture
    def api_client(self, admin_user, target_user):
        """Create a test client for the API with mocked authentication."""
        from api.main import app
        from api.middleware.auth import get_auth_context, get_current_admin

        # Create mock for user repository
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = target_user
        mock_user_repo.get_user_with_map_count.return_value = {
            "user": target_user,
            "map_count": 5,
        }

        # Create mock impersonation session repository
        mock_imp_repo = AsyncMock()
        mock_imp_session = create_mock_impersonation_session(admin_user, target_user)
        mock_imp_repo.create_session.return_value = mock_imp_session
        mock_imp_repo.get_active_session_for_admin.return_value = None

        # Create mock AuthContext for non-impersonating admin
        mock_auth_context = AuthContext(user=admin_user, is_impersonating=False)

        # Override dependencies
        app.dependency_overrides[get_current_admin] = lambda: admin_user
        app.dependency_overrides[get_auth_context] = lambda: mock_auth_context

        with patch(
            "api.routers.admin_router.UserRepository", return_value=mock_user_repo
        ), patch(
            "api.routers.admin_router.ImpersonationSessionRepository",
            return_value=mock_imp_repo,
        ):

            with TestClient(app) as client:
                yield client

        app.dependency_overrides.clear()

    def test_start_impersonation_success(self, api_client, target_user):
        """Test starting impersonation successfully."""
        response = api_client.post(f"/api/admin/impersonate/{target_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "token" not in data  # No more token in response
        assert data["user"]["email"] == target_user.email
        assert "Now impersonating" in data["message"]

    def test_start_impersonation_invalid_user_id(self, api_client):
        """Test starting impersonation with invalid user ID."""
        response = api_client.post("/api/admin/impersonate/invalid-uuid")

        assert response.status_code == 400
        data = response.json()
        error_message = data.get("detail") or data.get("message") or str(data)
        assert "Invalid user ID format" in error_message

    def test_start_impersonation_cannot_impersonate_self(self, admin_user):
        """Test that admin cannot impersonate themselves."""
        from api.main import app
        from api.middleware.auth import get_current_admin

        mock_user_repo = AsyncMock()
        mock_user_repo.get_user_with_map_count.return_value = {
            "user": admin_user,
            "map_count": 10,
        }

        app.dependency_overrides[get_current_admin] = lambda: admin_user

        with patch(
            "api.routers.admin_router.UserRepository", return_value=mock_user_repo
        ):
            with TestClient(app) as client:
                response = client.post(f"/api/admin/impersonate/{admin_user.id}")

        app.dependency_overrides.clear()

        assert response.status_code == 400
        data = response.json()
        error_message = data.get("detail") or data.get("message") or str(data)
        assert "Cannot impersonate yourself" in error_message

    def test_start_impersonation_cannot_impersonate_admin(self, admin_user):
        """Test that admin cannot impersonate another admin."""
        from api.main import app
        from api.middleware.auth import get_current_admin

        other_admin = create_mock_user(
            is_admin=True,
            email="other_admin@example.com",
        )

        mock_user_repo = AsyncMock()
        mock_user_repo.get_user_with_map_count.return_value = {
            "user": other_admin,
            "map_count": 10,
        }

        app.dependency_overrides[get_current_admin] = lambda: admin_user

        with patch(
            "api.routers.admin_router.UserRepository", return_value=mock_user_repo
        ):
            with TestClient(app) as client:
                response = client.post(f"/api/admin/impersonate/{other_admin.id}")

        app.dependency_overrides.clear()

        assert response.status_code == 403
        data = response.json()
        error_message = data.get("detail") or data.get("message") or str(data)
        assert "Cannot impersonate other administrators" in error_message

    def test_impersonation_status_not_impersonating(self, api_client, admin_user):
        """Test impersonation status when not impersonating."""
        response = api_client.get("/api/admin/impersonation-status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_impersonating"] is False
        assert data["real_admin"] is None
        assert data["current_user"]["email"] == admin_user.email

    @pytest.fixture
    def impersonating_client(self, admin_user, target_user):
        """Create a test client for an impersonating session."""
        from api.main import app
        from api.middleware.auth import get_auth_context

        imp_session = create_mock_impersonation_session(admin_user, target_user)

        # Create mock for user repository
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = admin_user
        mock_user_repo.get_user_with_map_count.side_effect = [
            {"user": target_user, "map_count": 5},  # For current user
            {"user": admin_user, "map_count": 10},  # For admin
        ]

        # Create mock impersonation session repository
        mock_imp_repo = AsyncMock()
        mock_imp_repo.deactivate_session.return_value = imp_session

        # Create mock AuthContext for impersonating session
        mock_auth_context = AuthContext(
            user=target_user,
            is_impersonating=True,
            real_admin=admin_user,
            impersonation_session_id=str(imp_session.id),
        )

        app.dependency_overrides[get_auth_context] = lambda: mock_auth_context

        with patch(
            "api.routers.admin_router.UserRepository", return_value=mock_user_repo
        ), patch(
            "api.routers.admin_router.ImpersonationSessionRepository",
            return_value=mock_imp_repo,
        ):

            with TestClient(app) as client:
                yield client

        app.dependency_overrides.clear()

    def test_stop_impersonation_success(self, impersonating_client, admin_user):
        """Test stopping impersonation successfully."""
        response = impersonating_client.post("/api/admin/stop-impersonation")

        assert response.status_code == 200
        data = response.json()
        assert "token" not in data  # No more token in response
        assert data["user"]["email"] == admin_user.email
        assert "Stopped impersonation" in data["message"]

    def test_stop_impersonation_not_impersonating(self, api_client):
        """Test stopping impersonation when not impersonating."""
        response = api_client.post("/api/admin/stop-impersonation")

        assert response.status_code == 400
        data = response.json()
        error_message = data.get("detail") or data.get("message") or str(data)
        assert "Not currently impersonating" in error_message

    def test_impersonation_status_when_impersonating(
        self, impersonating_client, target_user, admin_user
    ):
        """Test impersonation status when impersonating."""
        response = impersonating_client.get("/api/admin/impersonation-status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_impersonating"] is True
        assert data["real_admin"]["email"] == admin_user.email
        assert data["current_user"]["email"] == target_user.email


class TestMiddlewareImpersonation:
    """Test authentication middleware with impersonation sessions."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def admin_user(self):
        """Create an admin user."""
        return create_mock_admin()

    @pytest.fixture
    def target_user(self):
        """Create a target user."""
        return create_mock_target_user()

    @pytest.mark.asyncio
    async def test_middleware_returns_impersonated_user(
        self, mock_db, admin_user, target_user
    ):
        """Test that middleware returns impersonated user when session exists."""
        from api.middleware.auth import _get_auth_context_internal
        from fastapi.security import HTTPAuthorizationCredentials

        imp_session = create_mock_impersonation_session(admin_user, target_user)

        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "mock_jwt_token"

        # Mock AuthService and ImpersonationSessionRepository
        mock_auth_service = AsyncMock()
        mock_auth_service.verify_jwt.return_value = VerifyResult(user=admin_user)

        mock_imp_repo = AsyncMock()
        mock_imp_repo.get_active_session_for_admin.return_value = imp_session

        with patch(
            "api.middleware.auth.AuthService", return_value=mock_auth_service
        ), patch(
            "api.middleware.auth.ImpersonationSessionRepository",
            return_value=mock_imp_repo,
        ):
            context = await _get_auth_context_internal(mock_credentials, mock_db)

        assert context.user == target_user
        assert context.is_impersonating is True
        assert context.real_admin == admin_user
        assert context.impersonation_session_id == str(imp_session.id)

    @pytest.mark.asyncio
    async def test_middleware_returns_normal_user_no_session(
        self, mock_db, admin_user
    ):
        """Test that middleware returns normal user when no impersonation session."""
        from api.middleware.auth import _get_auth_context_internal
        from fastapi.security import HTTPAuthorizationCredentials

        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "mock_jwt_token"

        mock_auth_service = AsyncMock()
        mock_auth_service.verify_jwt.return_value = VerifyResult(user=admin_user)

        mock_imp_repo = AsyncMock()
        mock_imp_repo.get_active_session_for_admin.return_value = None

        with patch(
            "api.middleware.auth.AuthService", return_value=mock_auth_service
        ), patch(
            "api.middleware.auth.ImpersonationSessionRepository",
            return_value=mock_imp_repo,
        ):
            context = await _get_auth_context_internal(mock_credentials, mock_db)

        assert context.user == admin_user
        assert context.is_impersonating is False
        assert context.real_admin is None

    @pytest.mark.asyncio
    async def test_middleware_non_admin_no_impersonation_check(
        self, mock_db
    ):
        """Test that middleware skips impersonation check for non-admin users."""
        from api.middleware.auth import _get_auth_context_internal
        from fastapi.security import HTTPAuthorizationCredentials

        regular_user = create_mock_user(is_admin=False)

        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "mock_jwt_token"

        mock_auth_service = AsyncMock()
        mock_auth_service.verify_jwt.return_value = VerifyResult(user=regular_user)

        with patch(
            "api.middleware.auth.AuthService", return_value=mock_auth_service
        ):
            # ImpersonationSessionRepository should not be instantiated
            context = await _get_auth_context_internal(mock_credentials, mock_db)

        assert context.user == regular_user
        assert context.is_impersonating is False
        assert context.real_admin is None
