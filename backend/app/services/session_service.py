"""
Session Service.
Retrieves synthetic demo personas from customer_demo_accounts in Supabase,
resolves authoritative customer_unique_id, and manages persona sessions.
"""

from typing import List, Optional, Dict
from app.database.supabase_client import get_supabase_client
from app.schemas.session import (
    DemoPersonaSummary,
    CustomerContext,
    SessionResponse,
)
from app.core.session import create_session_token
from app.core.config import settings

_personas_cache: Optional[Dict[str, CustomerContext]] = None


def _load_personas_cache() -> Dict[str, CustomerContext]:
    """
    Loads all 25 demo accounts from customer_demo_accounts table into in-memory cache.
    """
    global _personas_cache
    if _personas_cache is not None:
        return _personas_cache

    client = get_supabase_client()
    resp = (
        client.table("customer_demo_accounts")
        .select("*")
        .order("demo_customer_id")
        .execute()
    )

    cache: Dict[str, CustomerContext] = {}
    for row in resp.data:
        ctx = CustomerContext(
            demo_customer_id=row["demo_customer_id"],
            customer_unique_id=row["customer_unique_id"],
            display_name=row["display_name"],
            demo_email=row["demo_email"],
            total_orders=row["total_orders"],
            primary_scenario=row["primary_scenario"],
            sample_order_id=row.get("sample_order_id"),
            customer_city=row.get("customer_city"),
            customer_state=row.get("customer_state"),
        )
        cache[ctx.demo_customer_id] = ctx

    _personas_cache = cache
    return _personas_cache


def get_all_personas() -> List[DemoPersonaSummary]:
    """
    Returns summary metadata for all 25 demo customer personas.
    """
    cache = _load_personas_cache()
    summaries = []
    for ctx in cache.values():
        summaries.append(
            DemoPersonaSummary(
                demo_customer_id=ctx.demo_customer_id,
                display_name=ctx.display_name,
                demo_email=ctx.demo_email,
                total_orders=ctx.total_orders,
                primary_scenario=ctx.primary_scenario,
                sample_order_id=ctx.sample_order_id,
                customer_city=ctx.customer_city,
                customer_state=ctx.customer_state,
            )
        )
    return summaries


def get_persona_by_id(demo_customer_id: str) -> Optional[CustomerContext]:
    """
    Resolves a demo_customer_id to its authoritative CustomerContext.
    """
    cache = _load_personas_cache()
    return cache.get(demo_customer_id)


def select_persona(demo_customer_id: str) -> SessionResponse:
    """
    Activates a demo persona and generates a signed session token.
    Raises ValueError if persona is not found.
    """
    customer = get_persona_by_id(demo_customer_id)
    if not customer:
        raise ValueError(f"Demo customer persona '{demo_customer_id}' not found.")

    token = create_session_token(customer)
    expires_in = settings.SESSION_EXPIRE_MINUTES * 60

    return SessionResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=expires_in,
        customer=customer,
    )
