"""Tests for application configuration."""

from app.config import Settings, get_settings


def test_settings_loads_defaults():
    """Settings should load with default values."""
    settings = get_settings()
    assert "postgresql" in settings.database_url
    assert isinstance(settings.serpapi_key, str)
    assert isinstance(settings.anthropic_api_key, str)


def test_settings_fields_exist():
    """Settings class should have all required fields."""
    fields = Settings.model_fields
    assert "database_url" in fields
    assert "serpapi_key" in fields
    assert "anthropic_api_key" in fields
