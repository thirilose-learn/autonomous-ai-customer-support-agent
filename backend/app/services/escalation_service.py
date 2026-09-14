"""
Escalation Service.
Manages persistent human support escalation tickets in Supabase PostgreSQL (support_escalations table).
Enforces strict cross-customer isolation: all operations bind exclusively to CustomerContext.customer_unique_id.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from app.database.supabase_client import get_supabase_client
from app.schemas.session import CustomerContext

logger = logging.getLogger(__name__)


def generate_ticket_id() -> str:
    """Generates a human-readable unique escalation ticket ID, e.g. ESC-F4A19B2C."""
    return f"ESC-{uuid.uuid4().hex[:8].upper()}"


def create_escalation_ticket(
    customer: CustomerContext,
    reason: str,
    priority: str = "normal",
    conversation_summary: Optional[str] = None,
    contact_email: Optional[str] = None,
    contact_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persists a new human escalation ticket in Supabase.
    CRITICAL: customer_unique_id is derived strictly from authenticated CustomerContext.
    contact_email and contact_phone store customer-provided contact details.
    Returns the persisted record dict upon success.
    Raises RuntimeError if database insertion fails.
    """
    if not reason or not reason.strip():
        raise ValueError("Escalation reason cannot be empty.")

    clean_priority = priority.strip().lower()
    if clean_priority not in ["normal", "high", "critical", "low"]:
        clean_priority = "normal"

    ticket_id = generate_ticket_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    payload = {
        "ticket_id": ticket_id,
        "customer_unique_id": customer.customer_unique_id,
        "demo_customer_id": customer.demo_customer_id,
        "reason": reason.strip(),
        "conversation_summary": conversation_summary.strip() if conversation_summary else None,
        "priority": clean_priority,
        "status": "open",
        "created_at": now_iso,
        "updated_at": now_iso,
        "contact_email": contact_email.strip() if contact_email else None,
        "contact_phone": contact_phone.strip() if contact_phone else None,
    }

    try:
        client = get_supabase_client()
        resp = client.table("support_escalations").insert(payload).execute()

        if not resp.data or len(resp.data) == 0:
            raise RuntimeError(f"Database insertion failed: no data returned from Supabase for ticket {ticket_id}.")

        persisted = resp.data[0]
        logger.info(f"Successfully persisted escalation ticket {ticket_id} for customer {customer.demo_customer_id}")
        return persisted
    except Exception as exc:
        logger.error(f"Failed to persist escalation ticket {ticket_id} to Supabase: {exc}")
        raise RuntimeError(f"Database persistence failure for escalation ticket: {str(exc)}") from exc


def get_escalation_by_id(
    ticket_id: str,
    customer: CustomerContext,
) -> Optional[Dict[str, Any]]:
    """
    Retrieves an escalation record ONLY if it belongs to the authenticated customer.
    If the ticket exists but belongs to a different customer, returns None.
    """
    client = get_supabase_client()
    resp = (
        client.table("support_escalations")
        .select("*")
        .eq("ticket_id", ticket_id.strip())
        .eq("customer_unique_id", customer.customer_unique_id)
        .execute()
    )
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    return None


def get_escalations_for_customer(
    customer: CustomerContext,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Retrieves recent escalation tickets strictly for the authenticated customer.
    """
    client = get_supabase_client()
    resp = (
        client.table("support_escalations")
        .select("*")
        .eq("customer_unique_id", customer.customer_unique_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []
