"""
Tests for ProviderSettings - TDD Implementation.

This module contains comprehensive tests for the provider settings,
including the new POI_PROVIDER and HERE_ENRICHMENT_ENABLED variables.
"""

import pytest
import os
from unittest.mock import patch

from api.providers.settings import ProviderSettings, get_settings, reset_settings


class TestProviderSettingsDefaults:
    """Test default values for provider settings."""

    def test_default_poi_provider_is_osm(self):
        """It should default POI_PROVIDER to 'osm'."""
        reset_settings()
        with patch.dict(os.environ, {}, clear=True):
            reset_settings()
            settings = ProviderSettings()
            assert settings.poi_provider == "osm"

    def test_default_here_enrichment_enabled_is_false(self):
        """It should default HERE_ENRICHMENT_ENABLED to False."""
        with patch.dict(os.environ, {}, clear=True):
            reset_settings()
            settings = ProviderSettings()
            assert settings.here_enrichment_enabled is False

    def test_default_google_places_enabled_is_true(self):
        """It should default GOOGLE_PLACES_ENABLED to True."""
        with patch.dict(os.environ, {}, clear=True):
            reset_settings()
            settings = ProviderSettings()
            assert settings.google_places_enabled is True

    def test_default_geo_primary_provider_is_osm(self):
        """It should default GEO_PRIMARY_PROVIDER to 'osm'."""
        with patch.dict(os.environ, {}, clear=True):
            reset_settings()
            settings = ProviderSettings()
            assert settings.geo_primary_provider == "osm"


class TestProviderSettingsEnvironmentVariables:
    """Test environment variable overrides for provider settings."""

    def test_poi_provider_from_env(self):
        """It should read POI_PROVIDER from environment variable."""
        with patch.dict(os.environ, {"POI_PROVIDER": "here"}):
            reset_settings()
            settings = ProviderSettings()
            assert settings.poi_provider == "here"

    def test_here_enrichment_enabled_from_env_true(self):
        """It should read HERE_ENRICHMENT_ENABLED as True from env."""
        with patch.dict(os.environ, {"HERE_ENRICHMENT_ENABLED": "true"}):
            reset_settings()
            settings = ProviderSettings()
            assert settings.here_enrichment_enabled is True

    def test_here_enrichment_enabled_from_env_false(self):
        """It should read HERE_ENRICHMENT_ENABLED as False from env."""
        with patch.dict(os.environ, {"HERE_ENRICHMENT_ENABLED": "false"}):
            reset_settings()
            settings = ProviderSettings()
            assert settings.here_enrichment_enabled is False

    def test_google_places_enabled_from_env_false(self):
        """It should read GOOGLE_PLACES_ENABLED as False from env."""
        with patch.dict(os.environ, {"GOOGLE_PLACES_ENABLED": "false"}):
            reset_settings()
            settings = ProviderSettings()
            assert settings.google_places_enabled is False

    def test_here_api_key_from_env(self):
        """It should read HERE_API_KEY from environment variable."""
        with patch.dict(os.environ, {"HERE_API_KEY": "test_key_12345"}):
            reset_settings()
            settings = ProviderSettings()
            assert settings.here_api_key == "test_key_12345"

    def test_google_places_api_key_from_env(self):
        """It should read GOOGLE_PLACES_API_KEY from environment variable."""
        with patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "google_test_key"}):
            reset_settings()
            settings = ProviderSettings()
            assert settings.google_places_api_key == "google_test_key"


class TestGetSettingsSingleton:
    """Test get_settings singleton behavior."""

    def test_get_settings_returns_same_instance(self):
        """It should return the same settings instance (singleton)."""
        reset_settings()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reset_settings_creates_new_instance(self):
        """It should create a new instance after reset_settings."""
        settings1 = get_settings()
        reset_settings()
        settings2 = get_settings()
        # After reset, should be different instances
        assert settings1 is not settings2


class TestProviderSettingsCacheTTL:
    """Test cache TTL configuration."""

    def test_get_cache_ttl_geocode(self):
        """It should return correct TTL for geocode operations."""
        settings = ProviderSettings()
        assert settings.get_cache_ttl("geocode") == settings.geo_cache_ttl_geocode

    def test_get_cache_ttl_route(self):
        """It should return correct TTL for route operations."""
        settings = ProviderSettings()
        assert settings.get_cache_ttl("route") == settings.geo_cache_ttl_route

    def test_get_cache_ttl_poi_search(self):
        """It should return correct TTL for POI search operations."""
        settings = ProviderSettings()
        assert settings.get_cache_ttl("poi_search") == settings.geo_cache_ttl_poi

    def test_get_cache_ttl_unknown_operation(self):
        """It should return default TTL for unknown operations."""
        settings = ProviderSettings()
        assert settings.get_cache_ttl("unknown_operation") == 3600  # 1 hour default


class TestProviderSettingsRateLimits:
    """Test rate limit configuration."""

    def test_get_rate_limit_osm(self):
        """It should return correct rate limit for OSM provider."""
        settings = ProviderSettings()
        assert settings.get_provider_rate_limit("osm") == settings.geo_rate_limit_osm

    def test_get_rate_limit_here(self):
        """It should return correct rate limit for HERE provider."""
        settings = ProviderSettings()
        assert settings.get_provider_rate_limit("here") == settings.geo_rate_limit_here

    def test_get_rate_limit_unknown_provider(self):
        """It should return default rate limit for unknown providers."""
        settings = ProviderSettings()
        assert settings.get_provider_rate_limit("unknown") == 1.0  # Default


class TestProviderSettingsValidation:
    """Test settings validation methods."""

    def test_validate_here_config_with_api_key(self):
        """It should validate HERE config when API key is present."""
        with patch.dict(os.environ, {
            "GEO_PRIMARY_PROVIDER": "here",
            "HERE_API_KEY": "test_key"
        }):
            reset_settings()
            settings = ProviderSettings()
            assert settings.validate_here_config() is True

    def test_validate_here_config_without_api_key(self):
        """It should fail validation when HERE is primary but no API key."""
        # Create settings object and manually set here_api_key to None
        # to test validation logic independent of environment
        settings = ProviderSettings()
        settings.geo_primary_provider = "here"
        settings.here_api_key = None
        # When HERE is selected but no API key, validation fails
        assert settings.validate_here_config() is False

    def test_validate_here_config_osm_no_key_needed(self):
        """It should pass validation for OSM even without HERE API key."""
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "osm"}, clear=True):
            reset_settings()
            settings = ProviderSettings()
            assert settings.validate_here_config() is True


class TestProviderSettingsToDict:
    """Test settings serialization."""

    def test_to_dict_contains_all_fields(self):
        """It should include all settings fields in dict representation."""
        settings = ProviderSettings()
        settings_dict = settings.to_dict()

        assert "poi_provider" in settings_dict
        assert "here_enrichment_enabled" in settings_dict
        assert "google_places_enabled" in settings_dict
        assert "geo_primary_provider" in settings_dict
        assert "here_api_key" in settings_dict
        assert "google_places_api_key" in settings_dict

    def test_to_dict_values_match(self):
        """It should have matching values in dict and attributes."""
        with patch.dict(os.environ, {
            "POI_PROVIDER": "here",
            "HERE_ENRICHMENT_ENABLED": "true"
        }):
            reset_settings()
            settings = ProviderSettings()
            settings_dict = settings.to_dict()

            assert settings_dict["poi_provider"] == settings.poi_provider
            assert settings_dict["here_enrichment_enabled"] == settings.here_enrichment_enabled


class TestProviderSettingsConfigMatrix:
    """Test provider configuration matrix scenarios."""

    def test_osm_poi_no_enrichment(self):
        """POI_PROVIDER=osm, HERE_ENRICHMENT_ENABLED=false."""
        with patch.dict(os.environ, {
            "POI_PROVIDER": "osm",
            "HERE_ENRICHMENT_ENABLED": "false",
            "GOOGLE_PLACES_ENABLED": "true"
        }):
            reset_settings()
            settings = ProviderSettings()
            assert settings.poi_provider == "osm"
            assert settings.here_enrichment_enabled is False
            assert settings.google_places_enabled is True

    def test_osm_poi_with_here_enrichment(self):
        """POI_PROVIDER=osm, HERE_ENRICHMENT_ENABLED=true."""
        with patch.dict(os.environ, {
            "POI_PROVIDER": "osm",
            "HERE_ENRICHMENT_ENABLED": "true",
            "HERE_API_KEY": "test_key",
            "GOOGLE_PLACES_ENABLED": "true"
        }):
            reset_settings()
            settings = ProviderSettings()
            assert settings.poi_provider == "osm"
            assert settings.here_enrichment_enabled is True
            assert settings.here_api_key == "test_key"
            assert settings.google_places_enabled is True

    def test_here_poi_provider(self):
        """POI_PROVIDER=here (enrichment N/A)."""
        with patch.dict(os.environ, {
            "POI_PROVIDER": "here",
            "HERE_API_KEY": "test_key",
            "GOOGLE_PLACES_ENABLED": "true"
        }):
            reset_settings()
            settings = ProviderSettings()
            assert settings.poi_provider == "here"
            assert settings.here_api_key == "test_key"
            # HERE enrichment is ignored when POI_PROVIDER=here
            # (POIs already come from HERE)
