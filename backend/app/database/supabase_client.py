"""
Supabase Database Client & Connectivity Module
Provides safe, authenticated client initialization and connection health verification.
Does not expose secrets in logs or exception traces.
"""

from typing import Optional, Dict, Any
from supabase import create_client, Client
from app.core.config import settings

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Initializes and returns the Supabase client using configured environment variables.
    Raises ValueError if required credentials are not configured.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase configuration missing: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is empty.")

    try:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
        return _supabase_client
    except Exception as e:
        # Sanitize exception message to prevent accidental credential leakage
        error_type = type(e).__name__
        raise ConnectionError(f"Failed to initialize Supabase client ({error_type}). Please check configuration.") from None


def check_supabase_connection() -> Dict[str, Any]:
    """
    Performs a safe, read-only connectivity check against the Supabase project.
    Does not require any application tables to exist.
    Does not mutate or create any database state.
    """
    try:
        client = get_supabase_client()
        # Safe read-only check: verify storage API access with the service role
        buckets = client.storage.list_buckets()
        return {
            "connected": True,
            "status": "online",
            "message": "Successfully authenticated and connected to Supabase project.",
            "storage_accessible": True,
            "bucket_count": len(buckets),
        }
    except Exception as e:
        error_type = type(e).__name__
        return {
            "connected": False,
            "status": "offline",
            "message": f"Connection failed ({error_type}). Ensure credentials are valid and network is available.",
            "storage_accessible": False,
        }
