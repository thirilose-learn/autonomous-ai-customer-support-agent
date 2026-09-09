import pytest
from app.core.config import settings
from app.database import get_supabase_client, check_supabase_connection
from supabase import Client


def test_supabase_config_present():
    """Verify that Supabase credentials exist in settings without exposing them."""
    assert bool(settings.SUPABASE_URL), "SUPABASE_URL is not configured."
    assert bool(settings.SUPABASE_SERVICE_ROLE_KEY), "SUPABASE_SERVICE_ROLE_KEY is not configured."
    assert settings.SUPABASE_URL.startswith("https://"), "SUPABASE_URL should be a valid HTTPS URL."


def test_supabase_client_initialization():
    """Verify that the Supabase client initializes cleanly with configured credentials."""
    client = get_supabase_client()
    assert client is not None
    assert isinstance(client, Client)


def test_supabase_live_connection():
    """Verify that the backend can successfully communicate with the remote Supabase project."""
    result = check_supabase_connection()
    assert result["connected"] is True, f"Supabase connection failed: {result.get('message')}"
    assert result["status"] == "online"
    assert result["storage_accessible"] is True


def test_no_secret_leakage_in_connection_result():
    """Verify that connection diagnostic output does not leak raw secret tokens."""
    result = check_supabase_connection()
    result_str = str(result)
    assert settings.SUPABASE_SERVICE_ROLE_KEY not in result_str
    # Verify no Authorization header or bearer token leaked
    assert "Bearer" not in result_str
