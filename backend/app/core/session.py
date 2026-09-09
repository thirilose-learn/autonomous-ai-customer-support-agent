"""
Session Token Manager.
Encodes and decodes signed JWT session tokens for demo customer personas.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import jwt
from app.core.config import settings
from app.schemas.session import CustomerContext

ALGORITHM = "HS256"


def create_session_token(customer: CustomerContext) -> str:
    """
    Creates a signed, tamper-proof session JWT containing the customer identity.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)
    
    payload: Dict[str, Any] = {
        "sub": customer.demo_customer_id,
        "cuid": customer.customer_unique_id,
        "name": customer.display_name,
        "email": customer.demo_email,
        "scenario": customer.primary_scenario,
        "orders": customer.total_orders,
        "sample_order_id": customer.sample_order_id,
        "city": customer.customer_city,
        "state": customer.customer_state,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    
    return jwt.encode(payload, settings.SESSION_SECRET_KEY, algorithm=ALGORITHM)


def decode_session_token(token: str) -> CustomerContext:
    """
    Decodes and validates a session JWT.
    Raises ValueError on expired or tampered tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SESSION_SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Session token has expired. Please select a persona again.")
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid session token: {str(exc)}")

    return CustomerContext(
        demo_customer_id=payload["sub"],
        customer_unique_id=payload["cuid"],
        display_name=payload.get("name", "Demo Customer"),
        demo_email=payload.get("email", ""),
        total_orders=payload.get("orders", 0),
        primary_scenario=payload.get("scenario", ""),
        sample_order_id=payload.get("sample_order_id"),
        customer_city=payload.get("city"),
        customer_state=payload.get("state"),
    )
