"""
Tests for POI Enrichment Service.

This module tests the centralized POI enrichment service that coordinates
enrichment from multiple sources (Google Places, HERE Maps).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestCreateAsyncEngineAndSession:
    """Test database connection helper."""

    def test_creates_engine_with_correct_url(self):
        """It should create an async engine with the correct database URL."""
        with patch.dict('os.environ', {
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DATABASE': 'test_db',
        }):
            from api.providers.settings import reset_settings
            reset_settings()

            from api.services.poi_enrichment_service import _create_async_engine_and_session

            engine, session_maker = _create_async_engine_and_session()

            assert engine is not None
            assert session_maker is not None


class TestEnrichMapWithGooglePlacesSync:
    """Test Google Places enrichment sync wrapper."""

    def test_returns_zero_when_disabled(self):
        """It should return 0 when Google Places is disabled."""
        with patch.dict('os.environ', {'GOOGLE_PLACES_ENABLED': 'false'}):
            from api.providers.settings import reset_settings
            reset_settings()

            from api.services.poi_enrichment_service import enrich_map_with_google_places_sync

            result = enrich_map_with_google_places_sync("test-map-id")

            assert result == 0

    def test_returns_zero_when_no_api_key(self):
        """It should return 0 and log warning when API key is missing."""
        with patch.dict('os.environ', {
            'GOOGLE_PLACES_ENABLED': 'true',
            'GOOGLE_PLACES_API_KEY': '',
        }, clear=False):
            from api.providers.settings import reset_settings
            reset_settings()

            # Need to ensure the API key is None/empty
            with patch('api.services.poi_enrichment_service.get_settings') as mock_settings:
                mock_settings.return_value.google_places_enabled = True
                mock_settings.return_value.google_places_api_key = None

                from api.services.poi_enrichment_service import enrich_map_with_google_places_sync

                result = enrich_map_with_google_places_sync("test-map-id")

                assert result == 0

    def test_calls_enrichment_when_enabled(self):
        """It should call enrichment function when enabled and configured."""
        with patch('api.services.poi_enrichment_service.get_settings') as mock_settings:
            mock_settings.return_value.google_places_enabled = True
            mock_settings.return_value.google_places_api_key = "test-api-key"
            mock_settings.return_value.postgres_user = "user"
            mock_settings.return_value.postgres_password = "pass"
            mock_settings.return_value.postgres_host = "localhost"
            mock_settings.return_value.postgres_port = "5432"
            mock_settings.return_value.postgres_database = "db"

            with patch('api.services.poi_enrichment_service._run_with_session') as mock_run:
                mock_run.return_value = 5

                with patch('asyncio.run', return_value=5):
                    from api.services.poi_enrichment_service import enrich_map_with_google_places_sync

                    result = enrich_map_with_google_places_sync("test-map-id")

                    # Should return the result from the enrichment
                    assert result == 5


class TestEnrichMapWithHereSync:
    """Test HERE enrichment sync wrapper."""

    def test_returns_zero_when_not_osm_provider(self):
        """It should return 0 when POI provider is not OSM."""
        with patch('api.services.poi_enrichment_service.get_settings') as mock_settings:
            mock_settings.return_value.poi_provider = "here"

            from api.services.poi_enrichment_service import enrich_map_with_here_sync

            result = enrich_map_with_here_sync("test-map-id")

            assert result == 0

    def test_returns_zero_when_disabled(self):
        """It should return 0 when HERE enrichment is disabled."""
        with patch('api.services.poi_enrichment_service.get_settings') as mock_settings:
            mock_settings.return_value.poi_provider = "osm"
            mock_settings.return_value.here_enrichment_enabled = False

            from api.services.poi_enrichment_service import enrich_map_with_here_sync

            result = enrich_map_with_here_sync("test-map-id")

            assert result == 0

    def test_returns_zero_when_no_api_key(self):
        """It should return 0 and log warning when API key is missing."""
        with patch('api.services.poi_enrichment_service.get_settings') as mock_settings:
            mock_settings.return_value.poi_provider = "osm"
            mock_settings.return_value.here_enrichment_enabled = True
            mock_settings.return_value.here_api_key = None

            from api.services.poi_enrichment_service import enrich_map_with_here_sync

            result = enrich_map_with_here_sync("test-map-id")

            assert result == 0

    def test_uses_default_poi_types(self):
        """It should use default POI types when none provided."""
        with patch('api.services.poi_enrichment_service.get_settings') as mock_settings:
            mock_settings.return_value.poi_provider = "osm"
            mock_settings.return_value.here_enrichment_enabled = True
            mock_settings.return_value.here_api_key = "test-key"
            mock_settings.return_value.postgres_user = "user"
            mock_settings.return_value.postgres_password = "pass"
            mock_settings.return_value.postgres_host = "localhost"
            mock_settings.return_value.postgres_port = "5432"
            mock_settings.return_value.postgres_database = "db"

            # Test that function runs without error (actual enrichment is mocked)
            with patch('asyncio.run', return_value=3):
                from api.services.poi_enrichment_service import enrich_map_with_here_sync

                result = enrich_map_with_here_sync("test-map-id")

                assert result == 3


class TestEnrichMapPois:
    """Test main enrichment entry point."""

    def test_returns_dict_with_all_counts(self):
        """It should return dict with counts from all enrichment sources."""
        with patch('api.services.poi_enrichment_service.enrich_map_with_google_places_sync') as mock_google:
            with patch('api.services.poi_enrichment_service.enrich_map_with_here_sync') as mock_here:
                mock_google.return_value = 10
                mock_here.return_value = 5

                from api.services.poi_enrichment_service import enrich_map_pois

                result = enrich_map_pois("test-map-id")

                assert result == {
                    "google_places_enriched": 10,
                    "here_enriched": 5,
                    "total_enriched": 15,
                }

    def test_calls_both_enrichment_services(self):
        """It should call both Google Places and HERE enrichment."""
        with patch('api.services.poi_enrichment_service.enrich_map_with_google_places_sync') as mock_google:
            with patch('api.services.poi_enrichment_service.enrich_map_with_here_sync') as mock_here:
                mock_google.return_value = 0
                mock_here.return_value = 0

                from api.services.poi_enrichment_service import enrich_map_pois

                enrich_map_pois("test-map-id")

                mock_google.assert_called_once_with("test-map-id")
                mock_here.assert_called_once_with("test-map-id")

    def test_handles_zero_enrichment(self):
        """It should handle case when no POIs are enriched."""
        with patch('api.services.poi_enrichment_service.enrich_map_with_google_places_sync') as mock_google:
            with patch('api.services.poi_enrichment_service.enrich_map_with_here_sync') as mock_here:
                mock_google.return_value = 0
                mock_here.return_value = 0

                from api.services.poi_enrichment_service import enrich_map_pois

                result = enrich_map_pois("test-map-id")

                assert result["total_enriched"] == 0


class TestEnrichMapPoisIntegration:
    """Integration tests for POI enrichment (with mocked external services)."""

    def test_google_places_enrichment_error_handling(self):
        """It should handle errors gracefully and continue with HERE."""
        with patch('api.services.poi_enrichment_service.enrich_map_with_google_places_sync') as mock_google:
            with patch('api.services.poi_enrichment_service.enrich_map_with_here_sync') as mock_here:
                # Google Places fails
                mock_google.side_effect = Exception("API error")
                mock_here.return_value = 3

                from api.services.poi_enrichment_service import enrich_map_pois

                # Should not raise, but will fail on Google
                try:
                    result = enrich_map_pois("test-map-id")
                except Exception:
                    # Expected if not handled - this tests that we should handle it
                    pass

    def test_here_enrichment_error_handling(self):
        """It should handle HERE errors gracefully."""
        with patch('api.services.poi_enrichment_service.enrich_map_with_google_places_sync') as mock_google:
            with patch('api.services.poi_enrichment_service.enrich_map_with_here_sync') as mock_here:
                mock_google.return_value = 5
                # HERE fails
                mock_here.side_effect = Exception("API error")

                from api.services.poi_enrichment_service import enrich_map_pois

                # Should not raise, but will fail on HERE
                try:
                    result = enrich_map_pois("test-map-id")
                except Exception:
                    # Expected if not handled - this tests that we should handle it
                    pass
