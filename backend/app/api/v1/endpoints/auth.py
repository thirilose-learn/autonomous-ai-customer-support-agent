"""
Authentication & Demo Session Endpoints.
Enables demo persona selection, session token generation, and customer profile resolution.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.session import (
    DemoPersonaSummary,
    CustomerContext,
    SelectPersonaRequest,
    SessionResponse,
)
from app.services import session_service
from app.api.deps import get_current_customer

router = APIRouter()


@router.get(
    "/personas",
    response_model=List[DemoPersonaSummary],
    status_code=status.HTTP_200_OK,
    summary="List Demo Customer Personas",
    description="Returns all 25 pre-configured deterministic demo accounts for test persona selection.",
)
def list_demo_personas() -> List[DemoPersonaSummary]:
    try:
        return session_service.get_all_personas()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load demo personas: {str(exc)}",
        )


@router.post(
    "/select-persona",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Select Active Demo Persona",
    description="Authenticates as a specific demo customer persona and returns a signed session token.",
)
def select_demo_persona(payload: SelectPersonaRequest) -> SessionResponse:
    try:
        session = session_service.select_persona(payload.demo_customer_id)
        return session
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Persona authentication failed: {str(exc)}",
        )


@router.get(
    "/me",
    response_model=CustomerContext,
    status_code=status.HTTP_200_OK,
    summary="Get Active Customer Profile",
    description="Resolves and returns the authenticated customer profile from the active session token.",
)
def get_authenticated_customer_profile(
    current_customer: CustomerContext = Depends(get_current_customer),
) -> CustomerContext:
    return current_customer


@router.post(
    "/logout",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Logout Demo Session",
    description="Stateless logout acknowledgment for client-side token discard.",
)
def logout_session() -> Dict[str, str]:
    return {"message": "Session terminated successfully."}
