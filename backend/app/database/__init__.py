"""Database integration package (Supabase / PostgreSQL)."""

from app.database.supabase_client import get_supabase_client, check_supabase_connection

__all__ = ["get_supabase_client", "check_supabase_connection"]
