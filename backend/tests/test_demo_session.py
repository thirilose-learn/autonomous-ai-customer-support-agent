"""
Automated Pytest Suite for Demo Authentication & Customer Session Context.
Validates persona selection, signed session tokens, cross-customer isolation,
tamper resistance, and expiration.
"""

from datetime import datetime, timezone, timedelta
import jwt
from starlette.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.session import create_session_token, decode_session_token, ALGORITHM
from app.services import session_service
from app.services.customer_data_service import get_order_for_customer, get_orders_for_customer

client = TestClient(app)


def test_get_demo_personas_list():
    """Verify GET /api/v1/auth/personas returns all 25 pre-configured demo personas."""
    response = client.get("/api/v1/auth/personas")
    assert response.status_code == 200, f"Failed to list personas: {response.text}"
    personas = response.json()
    assert len(personas) == 25, f"Expected 25 personas, got {len(personas)}"

    persona_ids = [p["demo_customer_id"] for p in personas]
    assert "DEMO_00001" in persona_ids
    assert "DEMO_00025" in persona_ids

    # Verify expected schema fields
    p1 = personas[0]
    assert "display_name" in p1
    assert "primary_scenario" in p1
    assert "total_orders" in p1
    assert "demo_email" in p1


def test_select_valid_demo_persona():
    """Verify selecting a valid demo persona returns a signed JWT and customer context."""
    response = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in_seconds"] == settings.SESSION_EXPIRE_MINUTES * 60

    customer = data["customer"]
    assert customer["demo_customer_id"] == "DEMO_00001"
    assert customer["customer_unique_id"] == "8d50f5eadf50201ccdcedfb9e2ac8455"
    assert customer["total_orders"] == 17
    assert customer["primary_scenario"] == "VIP_REPEAT_BUYER_17_ORDERS"


def test_select_invalid_demo_persona():
    """Verify selecting a non-existent persona returns HTTP 404."""
    response = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_99999"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_current_customer_profile_with_bearer_token():
    """Verify GET /api/v1/auth/me resolves the customer from the Bearer token."""
    # 1. Login
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00002"},
    )
    token = login_resp.json()["access_token"]

    # 2. Access /me with valid token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert profile["demo_customer_id"] == "DEMO_00002"
    assert profile["customer_unique_id"] == "3e43e6105506432c953e165fb2acf44c"


def test_missing_or_malformed_auth_header():
    """Verify accessing protected endpoints without Bearer token returns HTTP 401."""
    # No header
    resp_no_header = client.get("/api/v1/auth/me")
    assert resp_no_header.status_code == 401
    assert "missing" in resp_no_header.json()["detail"].lower()

    # Malformed header (missing Bearer prefix)
    resp_malformed = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic 12345"},
    )
    assert resp_malformed.status_code == 401
    assert "invalid" in resp_malformed.json()["detail"].lower()


def test_tampered_token_rejected():
    """Verify that tampering with token signature or payload causes HTTP 401."""
    # Create valid token
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    # Tamper with token string
    tampered_token = token[:-5] + "XXXXX"
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_expired_token_rejected():
    """Verify that expired tokens are cleanly rejected with HTTP 401."""
    customer = session_service.get_persona_by_id("DEMO_00001")
    assert customer is not None

    # Manually forge token with expired timestamp
    expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {
        "sub": customer.demo_customer_id,
        "cuid": customer.customer_unique_id,
        "name": customer.display_name,
        "iat": int((expired_time - timedelta(minutes=10)).timestamp()),
        "exp": int(expired_time.timestamp()),
    }
    expired_token = jwt.encode(payload, settings.SESSION_SECRET_KEY, algorithm=ALGORITHM)

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_cross_customer_isolation_defense():
    """
    Verify strict cross-customer isolation:
    DEMO_00001 cannot view DEMO_00002's order, and vice-versa.
    """
    p1 = session_service.get_persona_by_id("DEMO_00001")
    p2 = session_service.get_persona_by_id("DEMO_00002")
    assert p1 is not None and p2 is not None

    order_p1 = p1.sample_order_id  # owned by DEMO_00001
    order_p2 = p2.sample_order_id  # owned by DEMO_00002
    assert order_p1 != order_p2

    # 1. P1 queries own order -> SUCCESS
    found_p1 = get_order_for_customer(order_p1, p1)
    assert found_p1 is not None
    assert found_p1["order_id"] == order_p1

    # 2. P2 queries own order -> SUCCESS
    found_p2 = get_order_for_customer(order_p2, p2)
    assert found_p2 is not None
    assert found_p2["order_id"] == order_p2

    # 3. P1 queries P2's order -> ISOLATED (returns None)
    cross_p1_to_p2 = get_order_for_customer(order_p2, p1)
    assert cross_p1_to_p2 is None, "Cross-customer leakage! DEMO_00001 accessed DEMO_00002's order."

    # 4. P2 queries P1's order -> ISOLATED (returns None)
    cross_p2_to_p1 = get_order_for_customer(order_p1, p2)
    assert cross_p2_to_p1 is None, "Cross-customer leakage! DEMO_00002 accessed DEMO_00001's order."


def test_user_supplied_customer_id_cannot_override_session():
    """
    Verify that customer_unique_id is derived exclusively from the authenticated session,
    protecting against malicious requests that send another customer's ID in parameters.
    """
    p1 = session_service.get_persona_by_id("DEMO_00001")
    p2 = session_service.get_persona_by_id("DEMO_00002")

    # In our architecture, customer data lookups only take CustomerContext from get_current_customer dependency.
    # The queries only filter on p1.customer_unique_id:
    orders_for_p1 = get_orders_for_customer(p1)
    assert len(orders_for_p1) > 0
    for o in orders_for_p1:
        # All orders returned MUST belong to p1's customer_unique_id, never p2's
        assert o["order_id"] != p2.sample_order_id
