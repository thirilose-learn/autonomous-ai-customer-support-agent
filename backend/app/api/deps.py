"""
FastAPI Dependencies.
Extracts and validates the authenticated CustomerContext from request headers.
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from app.core.session import decode_session_token
from app.schemas.session import CustomerContext


def get_current_customer(
    authorization: Optional[str] = Header(None, description="Bearer <session_token>"),
) -> CustomerContext:
    """
    FastAPI dependency that enforces a valid, active demo customer session.
    Extracts Bearer token from Authorization header and decodes CustomerContext.
    Raises HTTP 401 if missing, expired, or tampered.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is missing. Please select a demo customer persona.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    try:
        customer_context = decode_session_token(token)
        return customer_context
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_optional_customer(
    authorization: Optional[str] = Header(None),
) -> Optional[CustomerContext]:
    """
    FastAPI dependency that returns CustomerContext if a valid session exists,
    or None if no session token was provided.
    """
    if not authorization:
        return None
    try:
        return get_current_customer(authorization=authorization)
    except HTTPException:
        return None
