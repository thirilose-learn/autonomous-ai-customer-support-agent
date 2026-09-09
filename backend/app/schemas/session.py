from typing import Optional
from pydantic import BaseModel, Field


class DemoPersonaSummary(BaseModel):
    demo_customer_id: str = Field(..., description="Unique demo account ID, e.g. DEMO_00001")
    display_name: str = Field(..., description="Human-readable synthetic persona name")
    demo_email: str = Field(..., description="Synthetic demo email address")
    total_orders: int = Field(..., description="Total lifetime orders placed by this customer")
    primary_scenario: str = Field(..., description="Test scenario description, e.g. VIP_REPEAT_BUYER_17_ORDERS")
    sample_order_id: Optional[str] = Field(None, description="Sample order ID for fast testing")
    customer_city: Optional[str] = Field(None, description="City location")
    customer_state: Optional[str] = Field(None, description="State code")


class CustomerContext(BaseModel):
    demo_customer_id: str = Field(..., description="Unique demo account ID")
    customer_unique_id: str = Field(..., description="Authoritative 32-char hex customer ID for database queries")
    display_name: str = Field(..., description="Human-readable synthetic persona name")
    demo_email: str = Field(..., description="Synthetic demo email address")
    total_orders: int = Field(..., description="Total lifetime orders placed by this customer")
    primary_scenario: str = Field(..., description="Test scenario description")
    sample_order_id: Optional[str] = Field(None, description="Sample order ID for fast testing")
    customer_city: Optional[str] = Field(None, description="City location")
    customer_state: Optional[str] = Field(None, description="State code")


class SelectPersonaRequest(BaseModel):
    demo_customer_id: str = Field(..., min_length=5, max_length=20, description="Demo customer ID to activate, e.g. DEMO_00001")


class SessionResponse(BaseModel):
    access_token: str = Field(..., description="Signed cryptographic session token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in_seconds: int = Field(..., description="Session validity duration in seconds")
    customer: CustomerContext = Field(..., description="Active customer profile context")
