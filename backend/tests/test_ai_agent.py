"""
Automated Pytest Suite for Level 5: AI Customer Support Agent & Tool Calling.
Validates:
1. Free hosted LLM initialization (Groq Cloud Developer Tier).
2. Pre-bound customer tools with strict cross-customer isolation defense.
3. Knowledge Base Policy RAG tool retrieval.
4. Escalation tool execution.
5. In-memory multi-turn dialogue management.
6. FastAPI chat endpoints (/api/v1/chat/message and /api/v1/chat/reset).
"""

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.session_service import get_persona_by_id
from app.agents.llm import get_chat_llm
from app.agents.tools.customer_tools import build_customer_tools
from app.agents.tools.policy_tool import search_policy_knowledge_base
from app.agents.tools.escalation_tool import build_escalation_tools
from app.agents.memory import (
    get_conversation_history,
    add_user_message,
    add_ai_message,
    clear_conversation,
)

client = TestClient(app)


def test_llm_factory_initialization():
    """Verify ChatGroq factory initializes with configured Groq models."""
    llm = get_chat_llm()
    assert llm is not None
    assert llm.model_name in [settings.GROQ_MODEL, settings.GROQ_FALLBACK_MODEL]


def test_customer_bound_tool_orders():
    """Verify get_my_orders returns orders strictly for the authenticated persona."""
    customer = get_persona_by_id("DEMO_00001")
    assert customer is not None

    tools = build_customer_tools(customer)
    order_tool = next(t for t in tools if t.name == "get_my_orders")

    result = order_tool.invoke({})
    assert "Found" in result or "order(s)" in result
    assert customer.display_name in result
    # Customer 00001 has order c2213109a2cc0e75d55585b7aaac6d97
    assert "c2213109a2cc0e75d55585b7aaac6d97" in result


def test_customer_bound_tool_order_details_ownership():
    """Verify get_my_order_details returns full item and pricing details for an owned order."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_customer_tools(customer)
    details_tool = next(t for t in tools if t.name == "get_my_order_details")

    # Owned order ID
    order_id = "c2213109a2cc0e75d55585b7aaac6d97"
    result = details_tool.invoke({"order_id": order_id})

    assert order_id in result
    assert "Delivered" in result or "Status" in result
    assert "Items Breakdown" in result
    assert "R$" in result


def test_customer_bound_tool_cross_customer_defense():
    """
    CRITICAL SECURITY TEST:
    Verify that if Customer A (DEMO_00001) attempts to inspect an order belonging
    to Customer B (DEMO_00002), the tool returns 'not found' with zero data leaked.
    """
    customer_a = get_persona_by_id("DEMO_00001")
    customer_b = get_persona_by_id("DEMO_00002")

    assert customer_a.customer_unique_id != customer_b.customer_unique_id
    order_b_id = customer_b.sample_order_id
    assert order_b_id is not None

    tools_a = build_customer_tools(customer_a)
    details_tool_a = next(t for t in tools_a if t.name == "get_my_order_details")

    # Customer A requests Customer B's order
    result = details_tool_a.invoke({"order_id": order_b_id})

    assert "was not found under your account" in result
    # Confirm no product info or price is returned
    assert "Items Breakdown:" not in result


def test_customer_bound_tool_payment_defense():
    """Verify get_my_payment_details prevents cross-customer payment data snooping."""
    customer_a = get_persona_by_id("DEMO_00001")
    customer_b = get_persona_by_id("DEMO_00002")
    order_b_id = customer_b.sample_order_id

    tools_a = build_customer_tools(customer_a)
    payment_tool_a = next(t for t in tools_a if t.name == "get_my_payment_details")

    result = payment_tool_a.invoke({"order_id": order_b_id})
    assert "was not found under your account" in result
    assert "Total Amount Paid:" not in result


def test_policy_rag_tool_execution():
    """Verify search_policy_knowledge_base retrieves policy excerpts from Level 4 pgvector."""
    result = search_policy_knowledge_base.invoke({
        "query": "What is the return window for items?",
        "category": "returns",
    })

    assert "Retrieved" in result or "policy excerpt" in result
    assert "Category:" in result
    assert any(term in result.lower() for term in ["return", "day", "refund", "condition"])


def test_escalation_tool_execution():
    """Verify request_human_escalation creates a formatted support ticket."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_escalation_tools(customer)
    esc_tool = tools[0]

    result = esc_tool.invoke({
        "reason": "Customer damaged item claim requiring supervisor review",
        "urgency": "high",
    })

    assert "Escalation Request Created Successfully" in result
    assert "Ticket ID: ESC-" in result
    assert customer.display_name in result
    assert "Urgency: HIGH" in result or "URGENCY: HIGH" in result


def test_conversation_memory_lifecycle():
    """Verify multi-turn memory buffers messages and resets cleanly."""
    conv_id = "test-session-mem-999"
    clear_conversation(conv_id)

    assert len(get_conversation_history(conv_id)) == 0

    add_user_message(conv_id, "Where is my order?")
    add_ai_message(conv_id, "Your order is delivered.")

    history = get_conversation_history(conv_id)
    assert len(history) == 2
    assert history[0].content == "Where is my order?"
    assert history[1].content == "Your order is delivered."

    cleared = clear_conversation(conv_id)
    assert cleared is True
    assert len(get_conversation_history(conv_id)) == 0


def test_chat_endpoint_unauthorized():
    """Verify POST /api/v1/chat/message returns HTTP 401 without Bearer token."""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "Where is my order?"},
    )
    assert response.status_code == 401
    assert "Session token is missing" in response.json()["detail"]


def test_chat_endpoint_invalid_token():
    """Verify POST /api/v1/chat/message returns HTTP 401 with an invalid token."""
    response = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": "Bearer invalid.token.payload"},
        json={"message": "Where is my order?"},
    )
    assert response.status_code == 401


def test_chat_endpoint_live_agent_turn():
    """
    End-to-End Test: Authenticates a demo customer and executes a live agent turn.
    Verifies response structure, tool invocation, and latency reporting.
    """
    # 1. Login as DEMO_00001
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 2. Query policy via agent
    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Can I return my item within 15 days?"},
    )
    assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.text}"
    data = chat_resp.json()

    assert "response" in data and len(data["response"]) > 0
    assert "intent" in data
    assert "tools_executed" in data
    assert "customer" in data
    assert data["customer"]["demo_customer_id"] == "DEMO_00001"
    assert "latency_ms" in data and data["latency_ms"] > 0


def test_chat_reset_endpoint():
    """Verify POST /api/v1/chat/reset clears memory for the active customer session."""
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    reset_resp = client.post(
        "/api/v1/chat/reset",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "reset"},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "success"
