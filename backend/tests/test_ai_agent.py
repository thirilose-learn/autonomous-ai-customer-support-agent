"""
Automated Pytest Suite for Level 5: AI Customer Support Agent & Tool Calling.
Validates:
1. Free hosted LLM initialization (Groq Cloud Developer Tier).
2. Pre-bound customer tools with strict cross-customer isolation defense.
3. Knowledge Base Policy RAG tool retrieval.
4. Intelligent / Conditional Escalation Policy:
   - "I want to speak to a human" does NOT create a ticket; asks for the underlying issue.
   - Routine order inquiries and policy queries do NOT escalate.
   - Mandatory contact collection & backend-authoritative validation (email/phone).
   - Supabase persistence with contact_email and contact_phone.
   - Cross-customer isolation defense on escalation tickets.
   - Database failure handling (no false success claims).
5. Conversation memory lifecycle.
6. English-default response regression.
"""

import re
import pytest
from unittest.mock import patch
from starlette.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.database.supabase_client import get_supabase_client
from app.services.session_service import get_persona_by_id
from app.services.escalation_service import (
    create_escalation_ticket,
    get_escalation_by_id,
    get_escalations_for_customer,
)
from app.services.escalation_policy import (
    validate_contact_info,
    extract_contact_info,
    is_generic_human_request,
    validate_escalation_readiness,
)
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


# =====================================================================
# 1. LLM & Tools Initialization
# =====================================================================

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
    assert "c2213109a2cc0e75d55585b7aaac6d97" in result


def test_customer_bound_tool_order_details_ownership():
    """Verify get_my_order_details returns full item and pricing details for an owned order."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_customer_tools(customer)
    details_tool = next(t for t in tools if t.name == "get_my_order_details")

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

    result = details_tool_a.invoke({"order_id": order_b_id})
    assert "was not found under your account" in result
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


def test_customer_payment_general_summary_tool():
    """Verify get_my_payment_details with omitted order_id returns multi-order payment summaries."""
    customer_3 = get_persona_by_id("DEMO_00003")
    tools_3 = build_customer_tools(customer_3)
    payment_tool_3 = next(t for t in tools_3 if t.name == "get_my_payment_details")

    # Call with empty/omitted order_id
    result = payment_tool_3.invoke({"order_id": None})
    assert "Payment Records for Recent Orders" in result
    assert "Customer 00003" in result
    assert "Total Paid: R$" in result
    assert "Payment #" in result


def test_policy_rag_tool_execution():
    """Verify search_policy_knowledge_base retrieves policy excerpts from Level 4 pgvector."""
    result = search_policy_knowledge_base.invoke({
        "query": "What is the return window for items?",
        "category": "returns",
    })

    assert "Retrieved" in result or "policy excerpt" in result
    assert "Category:" in result
    assert any(term in result.lower() for term in ["return", "day", "refund", "condition"])


# =====================================================================
# 2. Escalation Policy & Contact Validation Tests (Improvement 2)
# =====================================================================

def test_contact_validation_valid_email():
    """Verify validate_contact_info identifies and extracts valid email addresses."""
    valid, email, phone, err = validate_contact_info("support.user@example.com")
    assert valid is True
    assert email == "support.user@example.com"
    assert phone is None
    assert err == ""


def test_contact_validation_valid_phone():
    """Verify validate_contact_info identifies and extracts valid phone numbers."""
    valid, email, phone, err = validate_contact_info("+55 11 98765-4321")
    assert valid is True
    assert email is None
    assert phone == "+55 11 98765-4321"
    assert err == ""


def test_contact_validation_invalid_input():
    """Verify validate_contact_info rejects missing or invalid contact strings."""
    valid, email, phone, err = validate_contact_info("not-an-email-or-phone")
    assert valid is False
    assert "invalid" in err.lower()

    valid_empty, _, _, err_empty = validate_contact_info("")
    assert valid_empty is False
    assert "missing" in err_empty.lower()


def test_generic_human_request_detection():
    """Verify is_generic_human_request catches bare requests without issue descriptions."""
    assert is_generic_human_request("I want to speak to a human") is True
    assert is_generic_human_request("speak to a manager") is True
    assert is_generic_human_request("human support please") is True
    assert is_generic_human_request("Where is my order?") is False
    assert is_generic_human_request("My item arrived damaged in order c2213109a2cc0e75d55585b7aaac6d97") is False


def test_escalation_readiness_denies_bare_human_request():
    """Verify validate_escalation_readiness blocks escalation if reason is bare human request."""
    ready, _, _, err = validate_escalation_readiness(
        reason="I want to speak with a human",
        contact_info="client@example.com",
    )
    assert ready is False
    assert "requested a human but has not yet described their issue" in err


def test_escalation_tool_denies_missing_contact_info():
    """Verify request_human_escalation denies execution if contact info is missing."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_escalation_tools(customer)
    esc_tool = tools[0]

    result = esc_tool.invoke({
        "reason": "Unresolved damage claim following order investigation",
        "contact_info": "",
    })

    assert "Action Denied" in result
    assert "Contact information is missing" in result
    assert "ESC-" not in result


def test_escalation_tool_denies_invalid_contact_info():
    """Verify request_human_escalation denies execution if contact info is invalid."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_escalation_tools(customer)
    esc_tool = tools[0]

    result = esc_tool.invoke({
        "reason": "Unresolved damage claim following order investigation",
        "contact_info": "invalid_contact_handle",
    })

    assert "Action Denied" in result
    assert "invalid" in result.lower()
    assert "ESC-" not in result


def test_escalation_persists_with_valid_email():
    """Verify request_human_escalation creates ticket and persists contact_email in Supabase."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_escalation_tools(customer)
    esc_tool = tools[0]

    result = esc_tool.invoke({
        "reason": "Customer disputes carrier delivery confirmation for order c2213109a2cc0e75d55585b7aaac6d97",
        "contact_info": "alice.verified@example.com",
        "urgency": "high",
    })

    assert "Escalation Request Created Successfully" in result
    match = re.search(r"ESC-[A-F0-9]{8}", result)
    assert match is not None
    ticket_id = match.group(0)

    # Verify Supabase persistence with contact_email
    db_client = get_supabase_client()
    resp = db_client.table("support_escalations").select("*").eq("ticket_id", ticket_id).execute()
    assert len(resp.data) == 1
    record = resp.data[0]
    assert record["ticket_id"] == ticket_id
    assert record["customer_unique_id"] == customer.customer_unique_id
    assert record["contact_email"] == "alice.verified@example.com"
    assert record["priority"] == "high"
    assert record["status"] == "open"


def test_escalation_persists_with_valid_phone():
    """Verify request_human_escalation creates ticket and persists contact_phone in Supabase."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_escalation_tools(customer)
    esc_tool = tools[0]

    result = esc_tool.invoke({
        "reason": "Policy exception requested after checking return window",
        "contact_info": "+55 11 91234-5678",
        "urgency": "normal",
    })

    assert "Escalation Request Created Successfully" in result
    match = re.search(r"ESC-[A-F0-9]{8}", result)
    assert match is not None
    ticket_id = match.group(0)

    # Verify Supabase persistence with contact_phone
    db_client = get_supabase_client()
    resp = db_client.table("support_escalations").select("*").eq("ticket_id", ticket_id).execute()
    assert len(resp.data) == 1
    record = resp.data[0]
    assert record["ticket_id"] == ticket_id
    assert record["contact_phone"] == "+55 11 91234-5678"


def test_escalation_cross_customer_isolation():
    """Verify Customer A's escalation tickets cannot be accessed by Customer B."""
    customer_a = get_persona_by_id("DEMO_00001")
    customer_b = get_persona_by_id("DEMO_00002")

    ticket_record = create_escalation_ticket(
        customer=customer_a,
        reason="Confidential customer escalation",
        priority="normal",
        contact_email="customer_a@domain.com",
    )
    t_id = ticket_record["ticket_id"]

    # Customer B attempts lookup
    b_lookup = get_escalation_by_id(ticket_id=t_id, customer=customer_b)
    assert b_lookup is None

    # Customer A lookup succeeds
    a_lookup = get_escalation_by_id(ticket_id=t_id, customer=customer_a)
    assert a_lookup is not None
    assert a_lookup["ticket_id"] == t_id


def test_escalation_db_failure_handling():
    """Verify database failure reports clear error without claiming false success."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_escalation_tools(customer)
    esc_tool = tools[0]

    with patch("app.agents.tools.escalation_tool.create_escalation_ticket", side_effect=RuntimeError("Database write timeout")):
        result = esc_tool.invoke({
            "reason": "Test unresolvable issue requiring human review",
            "contact_info": "test@example.com",
            "urgency": "normal",
        })

    assert "Escalation Failed" in result
    assert "The ticket was NOT created" in result
    assert "Created Successfully" not in result


# =====================================================================
# 3. Conversational End-to-End Tests via FastAPI
# =====================================================================

def test_direct_human_request_asks_for_issue_no_ticket():
    """
    IMPROVEMENT 2 TEST:
    Verify 'I want to speak to a human' does NOT create an escalation ticket,
    and instead asks the customer what issue they need help with.
    """
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "I want to speak to a human."},
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()

    # Must NOT execute escalation tool
    assert "request_human_escalation" not in data["tools_executed"]
    assert "ESC-" not in data["response"]
    # Should ask what issue they need assistance with
    assert any(w in data["response"].lower() for w in ["help", "issue", "order", "assist", "problem", "describe"])


def test_supervisor_review_button_asks_for_issue_no_ticket():
    """
    Verify predefined quick inquiry 'I need to speak with a supervisor regarding an issue.'
    does NOT immediately create an escalation ticket, and asks what issue/order is involved.
    """
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "I need to speak with a supervisor regarding an issue.", "conversation_id": "test-supervisor-button-flow"},
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()

    # Must NOT execute escalation tool
    assert "request_human_escalation" not in data["tools_executed"]
    assert "ESC-" not in data["response"]
    # Must ask what issue/order needs help
    assert any(w in data["response"].lower() for w in ["help", "issue", "order", "assist", "problem", "describe"])


def test_customer_inquiry_what_did_i_buy_latest_order():
    """
    Verify inquiry 'What did I buy in my latest order?' resolves the customer's
    latest order items and products without error.
    """
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "What did I buy in my latest order?", "conversation_id": "test-latest-items-flow"},
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()

    # Should execute order tools
    assert any(t in data["tools_executed"] for t in ["get_my_orders", "get_my_order_details"])
    # Should include products or categories in response
    assert len(data["response"]) > 20
    assert any(w in data["response"].lower() for w in ["construction", "tool", "category", "price", "d3582fd5ccccd9cb229a63dfb417c86f"])


def test_routine_order_inquiry_no_escalation():
    """Verify routine order inquiries use order tools and do NOT escalate."""
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Where is my order?"},
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()

    assert data["intent"] == "ORDER_INQUIRY"
    assert "get_my_orders" in data["tools_executed"]
    assert "request_human_escalation" not in data["tools_executed"]
    assert "ESC-" not in data["response"]


def test_routine_policy_question_no_escalation():
    """Verify policy inquiries use search_policy_knowledge_base and do NOT escalate."""
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "What is your refund and return policy?"},
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()

    assert data["intent"] == "POLICY_RAG"
    assert "search_policy_knowledge_base" in data["tools_executed"]
    assert "request_human_escalation" not in data["tools_executed"]


def test_conversation_memory_lifecycle():
    """Verify multi-turn memory buffers messages and resets cleanly."""
    conv_id = "test-session-mem-polish"
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


def test_regression_english_query_receives_english_response():
    """Verify English customer inquiries receive responses strictly in English."""
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Where is my order?"},
    )
    assert chat_resp.status_code == 200
    text = chat_resp.json()["response"]

    portuguese_markers = [
        "olá", "aqui está", "seus pedidos", "mais recentes",
        "política de devolução", "não, a devolução", "dias corridos"
    ]
    for marker in portuguese_markers:
        assert marker not in text.lower(), f"Detected unexpected language marker '{marker}' in response: {text}"

    assert any(w in text.lower() for w in ["order", "status", "delivered", "shipped", "tracking", "purchase"])


def test_auto_escalation_after_contact_supplied():
    """
    REGRESSION TEST:
    Customer reports an escalation-worthy issue (supervisor replacement review)
    -> Agent investigates with tools & requests email/phone
    -> Customer provides email: "My email is myemail@test.com"
    -> Agent AUTOMATICALLY invokes request_human_escalation and returns real Ticket ID
    -> Customer does NOT need to explicitly say 'escalate' again.
    """
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    # Reset session memory first
    client.post(
        "/api/v1/chat/reset",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "reset"},
    )

    # Turn 1: Customer describes damaged product and requests supervisor replacement review
    turn1_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "My delivered order c2213109a2cc0e75d55585b7aaac6d97 arrived severely damaged and I need a supervisor replacement review"},
    )
    assert turn1_resp.status_code == 200
    turn1_data = turn1_resp.json()

    # Agent must NOT claim to have generated or emailed a label directly
    assert "initiating the return-label email" not in turn1_data["response"].lower()
    assert "i'll generate a prepaid return" not in turn1_data["response"].lower()

    # Turn 2: Customer provides email
    turn2_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "My email is myemail@test.com"},
    )
    assert turn2_resp.status_code == 200
    turn2_data = turn2_resp.json()

    # MUST have executed request_human_escalation automatically
    assert "request_human_escalation" in turn2_data["tools_executed"]

    # Must disclose real ticket ID
    match = re.search(r"ESC-[A-F0-9]{8}", turn2_data["response"])
    assert match is not None, f"Expected Ticket ID in turn 2 response: {turn2_data['response']}"
    ticket_id = match.group(0)

    # Verify ticket was persisted in Supabase with customer's email
    db_client = get_supabase_client()
    db_resp = db_client.table("support_escalations").select("*").eq("ticket_id", ticket_id).execute()
    assert len(db_resp.data) == 1
    record = db_resp.data[0]
    assert record["ticket_id"] == ticket_id
    assert record["contact_email"] == "myemail@test.com"
    assert record["status"] == "open"


def test_capability_boundaries_no_false_label_or_email_claims():
    """
    REGRESSION TEST:
    Verify that the agent never claims it can generate, print, or email shipping labels,
    or dispatch replacement packages directly.
    """
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]

    chat_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Can you email me a prepaid return shipping label right now for my order?"},
    )
    assert chat_resp.status_code == 200
    text = chat_resp.json()["response"].lower()

    # Must NOT claim that it generates or emails labels directly
    assert "i'll generate a prepaid return" not in text
    assert "initiating the return-label email now" not in text
    assert "i will generate a prepaid return label" not in text


# =====================================================================
# 7. Per-Persona Conversation & Memory Isolation Regression Tests
# =====================================================================

def test_persona_conversation_memory_isolation_and_switching():
    """
    REGRESSION TEST:
    Verify complete conversation state and backend agent memory isolation
    when switching between DEMO_00001 -> DEMO_00002 -> DEMO_00001:
    1. DEMO_00001 conversation history is isolated to DEMO_00001.
    2. DEMO_00002 starts with a clean memory state.
    3. DEMO_00001 messages NEVER leak to DEMO_00002.
    4. DEMO_00002 messages NEVER leak to DEMO_00001.
    5. Switching back to DEMO_00001 restores DEMO_00001 context with no cross-contamination.
    """
    # 1. Login as DEMO_00001
    auth1 = client.post("/api/v1/auth/select-persona", json={"demo_customer_id": "DEMO_00001"})
    token1 = auth1.json()["access_token"]

    # 2. Login as DEMO_00002
    auth2 = client.post("/api/v1/auth/select-persona", json={"demo_customer_id": "DEMO_00002"})
    token2 = auth2.json()["access_token"]

    # Reset both sessions
    client.post("/api/v1/chat/reset", headers={"Authorization": f"Bearer {token1}"}, json={"message": "reset"})
    client.post("/api/v1/chat/reset", headers={"Authorization": f"Bearer {token2}"}, json={"message": "reset"})

    session1_id = "session-DEMO_00001"
    session2_id = "session-DEMO_00002"

    assert len(get_conversation_history(session1_id)) == 0
    assert len(get_conversation_history(session2_id)) == 0

    # 3. DEMO_00001 sends a message
    resp1 = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token1}"},
        json={"message": "What is my total number of orders on file?"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["customer"]["demo_customer_id"] == "DEMO_00001"

    # Verify DEMO_00001 session has memory, while DEMO_00002 session remains completely empty
    hist1 = get_conversation_history(session1_id)
    hist2 = get_conversation_history(session2_id)
    assert len(hist1) >= 2
    assert len(hist2) == 0

    # 4. Switch to DEMO_00002 and send a message
    resp2 = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token2}"},
        json={"message": "What city and state am I located in?"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["customer"]["demo_customer_id"] == "DEMO_00002"

    # Verify DEMO_00002 session only has DEMO_00002's memory
    hist2_after = get_conversation_history(session2_id)
    assert len(hist2_after) >= 2
    # Ensure no DEMO_00001 user prompts or tool responses exist in DEMO_00002 history
    for msg in hist2_after:
        assert "What is my total number of orders on file?" not in msg.content
        assert "DEMO_00001" not in msg.content

    # 5. Switch back to DEMO_00001 and send a follow-up
    resp1_followup = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token1}"},
        json={"message": "Can you summarize what we just discussed?"},
    )
    assert resp1_followup.status_code == 200
    data1_followup = resp1_followup.json()
    assert data1_followup["customer"]["demo_customer_id"] == "DEMO_00001"

    # Verify DEMO_00001 history does not contain DEMO_00002 query
    hist1_after = get_conversation_history(session1_id)
    for msg in hist1_after:
        assert "What city and state am I located in?" not in msg.content


def test_custom_conversation_id_backend_namespacing():
    """
    Verify that even if two different personas provide the identical conversation_id,
    the backend strictly namespaces them by authenticated demo_customer_id, preventing collision.
    """
    auth1 = client.post("/api/v1/auth/select-persona", json={"demo_customer_id": "DEMO_00001"})
    token1 = auth1.json()["access_token"]
    auth2 = client.post("/api/v1/auth/select-persona", json={"demo_customer_id": "DEMO_00002"})
    token2 = auth2.json()["access_token"]

    shared_conv_id = "shared-support-thread"

    # Both send messages with the identical conversation_id
    resp1 = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token1}"},
        json={"message": "Hello from DEMO 1", "conversation_id": shared_conv_id},
    )
    assert resp1.status_code == 200
    assert resp1.json()["conversation_id"] == f"DEMO_00001:{shared_conv_id}"

    resp2 = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token2}"},
        json={"message": "Hello from DEMO 2", "conversation_id": shared_conv_id},
    )
    assert resp2.status_code == 200
    assert resp2.json()["conversation_id"] == f"DEMO_00002:{shared_conv_id}"

    # Verify both exist independently in the store
    mem1 = get_conversation_history(f"DEMO_00001:{shared_conv_id}")
    mem2 = get_conversation_history(f"DEMO_00002:{shared_conv_id}")

    assert any("Hello from DEMO 1" in m.content for m in mem1)
    assert not any("Hello from DEMO 2" in m.content for m in mem1)

    assert any("Hello from DEMO 2" in m.content for m in mem2)
    assert not any("Hello from DEMO 1" in m.content for m in mem2)


# =====================================================================
# 7. Targeted Regression Tests: Escalation Precision & Product Context
# =====================================================================

def test_generic_human_request_includes_predefined_button_text():
    """Verify is_generic_human_request catches predefined button text and variants."""
    assert is_generic_human_request("I need to speak with a supervisor regarding an issue.") is True
    assert is_generic_human_request("I need to speak with a supervisor regarding an issue") is True
    assert is_generic_human_request("🎫 Request supervisor review") is True
    assert is_generic_human_request("Request supervisor review") is True
    assert is_generic_human_request("I want to speak with a supervisor") is True
    assert is_generic_human_request("I want to speak to a supervisor") is True
    # Substantive complaints must NOT be classified as generic
    assert is_generic_human_request("My delivered order arrived damaged and I need a replacement.") is False
    assert is_generic_human_request("My order contains the wrong item and I want a supervisor to review it.") is False
    assert is_generic_human_request("My refund was denied and I want a supervisor to review the case.") is False


def test_escalation_readiness_denies_supervisor_button_text():
    """Verify validate_escalation_readiness blocks escalation on generic supervisor button text."""
    ready, _, _, err = validate_escalation_readiness(
        reason="I need to speak with a supervisor regarding an issue.",
        contact_info="customer@example.com",
    )
    assert ready is False
    assert "not yet described their issue" in err.lower() or "substantive issue" in err.lower()


def test_escalation_readiness_accepts_substantive_reason():
    """Verify validate_escalation_readiness passes when a substantive issue is stated."""
    ready, email, phone, err = validate_escalation_readiness(
        reason="My delivered order arrived severely damaged and I need a supervisor replacement review.",
        contact_info="customer@example.com",
    )
    assert ready is True
    assert email == "customer@example.com"
    assert err == ""


def test_pending_escalation_requires_substantive_issue_case_c():
    """
    CASE C: Customer clicks/types generic supervisor request, agent asks for issue,
    customer provides email BEFORE stating an issue.
    detect_pending_escalation_intent MUST return is_pending=False to avoid premature ticket creation.
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.services.escalation_policy import detect_pending_escalation_intent

    history = [
        HumanMessage(content="I need to speak with a supervisor regarding an issue."),
        AIMessage(content="I'd be happy to connect you with a supervisor. Could you tell me what issue or order you need help with?"),
    ]

    is_pending, email, phone, reason, order_id = detect_pending_escalation_intent(history, "my email is customer@example.com")
    assert is_pending is False
    assert email == "customer@example.com"
    assert reason is None


def test_pending_escalation_succeeds_when_both_present():
    """
    CASE B: Substantive issue was stated, customer subsequently provides email.
    detect_pending_escalation_intent MUST return is_pending=True with the substantive reason.
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.services.escalation_policy import detect_pending_escalation_intent

    history = [
        HumanMessage(content="My delivered order arrived damaged and I need a replacement."),
        AIMessage(content="I'm sorry to hear that. Please provide your email address so a supervisor can follow up."),
    ]

    is_pending, email, phone, reason, order_id = detect_pending_escalation_intent(history, "my email is customer@example.com")
    assert is_pending is True
    assert email == "customer@example.com"
    assert reason is not None
    assert "damaged" in reason.lower()


def test_customer_orders_includes_item_product_summary():
    """Verify get_my_orders returns item counts and formatted product categories."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_customer_tools(customer)
    order_tool = next(t for t in tools if t.name == "get_my_orders")

    output = order_tool.invoke({})
    assert "Found" in output
    assert "Total Items:" in output
    assert "Products:" in output
    assert "c2213109a2cc0e75d55585b7aaac6d97" in output


def test_customer_order_details_default_latest_order():
    """Verify get_my_order_details automatically resolves to the latest order when order_id is omitted."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_customer_tools(customer)
    details_tool = next(t for t in tools if t.name == "get_my_order_details")

    output = details_tool.invoke({})
    assert "Order Details for" in output
    assert "Most Recent Order" in output or "c2213109a2cc0e75d55585b7aaac6d97" in output
    assert "Items Breakdown" in output
    assert "R$" in output
    assert "Product Subtotal" in output


def test_customer_order_details_cross_customer_defense():
    """Verify Customer A cannot inspect Customer B's order items/products."""
    customer_a = get_persona_by_id("DEMO_00001")
    customer_b = get_persona_by_id("DEMO_00002")
    tools_a = build_customer_tools(customer_a)
    details_tool = next(t for t in tools_a if t.name == "get_my_order_details")

    # Order belonging strictly to Customer B
    order_b_id = customer_b.sample_order_id
    output = details_tool.invoke({"order_id": order_b_id})

    assert f"Order '{order_b_id}' was not found under your account" in output


def test_format_category_name_utility():
    """Verify category name formatting produces customer-friendly English titles."""
    from app.services.customer_data_service import format_category_name

    assert format_category_name("bed_bath_table") == "Bed Bath & Table"
    assert format_category_name("sports_leisure") == "Sports & Leisure"
    assert format_category_name("furniture_decor") == "Furniture & Decor"
    assert format_category_name("home_construction") == "Home Construction"
    assert format_category_name("") == "General Merchandise"
    assert format_category_name(None) == "General Merchandise"


def test_missing_order_details_truthful_response():
    """Verify that looking up a nonexistent order returns a truthful not-found message."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_customer_tools(customer)
    details_tool = next(t for t in tools if t.name == "get_my_order_details")

    nonexistent_id = "00000000000000000000000000000000"
    output = details_tool.invoke({"order_id": nonexistent_id})

    assert f"Order '{nonexistent_id}' was not found under your account" in output
    assert "Delivered" not in output
    assert "ESC-" not in output


def test_case_c_contact_without_issue_no_ticket_created():
    """
    Verify Case C conversational flow:
    Turn 1: User asks for supervisor generically -> Agent asks what issue/order.
    Turn 2: User gives email before stating issue -> Agent must NOT create ticket.
    """
    login_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = login_resp.json()["access_token"]
    conv_id = "test-case-c-flow"

    # Turn 1: Generic supervisor request
    t1_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "I want to speak with a supervisor.", "conversation_id": conv_id},
    )
    assert t1_resp.status_code == 200
    assert "request_human_escalation" not in t1_resp.json()["tools_executed"]
    assert "ESC-" not in t1_resp.json()["response"]

    # Turn 2: User provides email before stating issue
    t2_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "My email is customer.test@example.com", "conversation_id": conv_id},
    )
    assert t2_resp.status_code == 200
    t2_data = t2_resp.json()

    # Must STILL NOT create ticket because there is no substantive reason yet!
    assert "request_human_escalation" not in t2_data["tools_executed"]
    assert "ESC-" not in t2_data["response"]


# =====================================================================
# 8. Deterministic Precision Tests: Escalation Boundary & Disambiguation
# =====================================================================

def test_escalation_boundary_detection():
    """Verify get_last_escalation_boundary identifies the index of the last ticket created."""
    from langchain_core.messages import HumanMessage, AIMessage
    from app.services.escalation_policy import get_last_escalation_boundary

    history_no_ticket = [
        HumanMessage(content="I want to speak with a human"),
        AIMessage(content="What issue do you need help with?"),
    ]
    assert get_last_escalation_boundary(history_no_ticket) == -1

    history_with_ticket = [
        HumanMessage(content="My delivered order arrived damaged"),
        AIMessage(content="Ticket ESC-DDF100A6 has been created for your issue."),
        HumanMessage(content="What did I buy in my latest order?"),
        AIMessage(content="You bought Bed Bath & Table."),
    ]
    # The ticket message is at index 1
    assert get_last_escalation_boundary(history_with_ticket) == 1


def test_post_escalation_unrelated_queries_do_not_re_escalate():
    """
    CRITICAL REGRESSION TEST:
    After a ticket (e.g. ESC-DDF100A6) has been generated:
    Subsequent unrelated customer inquiries (latest order items, payment methods, order tracking)
    must NOT inherit the old escalation intent or trigger request_human_escalation!
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.services.escalation_policy import detect_pending_escalation_intent

    # History where an escalation ticket was successfully created on Turn 3
    history_after_ticket = [
        HumanMessage(content="I need a supervisor."),
        AIMessage(content="Please provide your email and describe the issue."),
        HumanMessage(content="My email is customer.test@example.com and my order arrived broken."),
        AIMessage(content="I have escalated your request under Ticket ESC-DDF100A6."),
    ]

    customer = get_persona_by_id("DEMO_00001")

    # Turn 4: "What did I buy in my latest order?"
    is_pending, email, phone, reason, order_id = detect_pending_escalation_intent(
        history_after_ticket, "What did I buy in my latest order?", customer=customer
    )
    assert is_pending is False
    assert reason is None

    # Turn 5: "What payment method was used for my orders?"
    is_pending_pay, _, _, reason_pay, _ = detect_pending_escalation_intent(
        history_after_ticket, "What payment method was used for my orders?", customer=customer
    )
    assert is_pending_pay is False
    assert reason_pay is None

    # Turn 6: "Where is my order?"
    is_pending_track, _, _, reason_track, _ = detect_pending_escalation_intent(
        history_after_ticket, "Where is my order?", customer=customer
    )
    assert is_pending_track is False
    assert reason_track is None


def test_new_substantive_complaint_after_ticket_can_escalate():
    """
    Verify that a genuinely NEW complaint after an old ticket can start a new escalation flow
    and is not permanently blocked.
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.services.escalation_policy import detect_pending_escalation_intent

    history_after_ticket = [
        HumanMessage(content="My email is customer.test@example.com"),
        HumanMessage(content="My order arrived broken."),
        AIMessage(content="I have escalated your request under Ticket ESC-DDF100A6."),
    ]

    customer = get_persona_by_id("DEMO_00001")

    # User introduces a brand new substantive issue specifying the order
    new_msg = "I have another issue. Order c2213109a2cc0e75d55585b7aaac6d97 contains the wrong item."
    is_pending, email, phone, reason, order_id = detect_pending_escalation_intent(
        history_after_ticket, new_msg, customer=customer
    )
    assert is_pending is True
    assert email == "customer.test@example.com"
    assert "wrong item" in reason.lower()
    assert order_id == "c2213109a2cc0e75d55585b7aaac6d97"


def test_multi_order_customer_ambiguous_order_blocks_escalation():
    """
    Verify that for a customer with MULTIPLE orders (e.g. DEMO_00001 with 17 orders),
    a complaint like 'My delivered order arrived severely damaged' WITHOUT identifying which
    order is affected does NOT immediately escalate, requiring order disambiguation first.
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.services.escalation_policy import detect_pending_escalation_intent

    customer = get_persona_by_id("DEMO_00001")
    assert customer.total_orders > 1

    history = [
        HumanMessage(content="I want to speak with a supervisor."),
        AIMessage(content="I'd be happy to help. What issue or order needs assistance?"),
        HumanMessage(content="My email is customer.test@example.com"),
        AIMessage(content="Thank you. Could you describe what happened?"),
    ]

    # User describes substantive damage, but does NOT identify which of their 17 orders was damaged!
    user_msg = "My delivered order arrived severely damaged and I need a replacement."
    is_pending, email, phone, reason, order_id = detect_pending_escalation_intent(
        history, user_msg, customer=customer
    )

    # Must NOT be marked as pending escalation yet, so agent prompts for order ID / date / product!
    assert is_pending is False
    assert email == "customer.test@example.com"
    assert reason is not None  # Reason was recognized, but order context is missing


def test_multi_order_customer_with_order_id_escalates():
    """
    Verify that when a multi-order customer provides the specific order ID or product,
    escalation readiness is fulfilled.
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from app.services.escalation_policy import detect_pending_escalation_intent

    customer = get_persona_by_id("DEMO_00001")

    history = [
        HumanMessage(content="My email is customer.test@example.com"),
        AIMessage(content="Thank you."),
    ]

    user_msg = "My order c2213109a2cc0e75d55585b7aaac6d97 arrived damaged and I need a replacement."
    is_pending, email, phone, reason, order_id = detect_pending_escalation_intent(
        history, user_msg, customer=customer
    )

    assert is_pending is True
    assert email == "customer.test@example.com"
    assert order_id == "c2213109a2cc0e75d55585b7aaac6d97"


def test_single_order_customer_auto_resolves_order():
    """
    Verify that a customer with ONLY 1 order does not need to specify the order ID
    because the affected purchase is unambiguous.
    """
    from app.services.escalation_policy import detect_pending_escalation_intent
    from app.schemas.session import CustomerContext

    single_order_customer = CustomerContext(
        demo_customer_id="DEMO_TEST_SINGLE",
        customer_unique_id="test_unique_id_single_001",
        display_name="Single Order Customer",
        demo_email="single.order@example.com",
        total_orders=1,
        primary_scenario="SINGLE_ORDER_CUSTOMER",
        sample_order_id="single_order_abc123",
    )

    user_msg = "My order arrived damaged. My email is single.order@example.com."
    is_pending, email, phone, reason, order_id = detect_pending_escalation_intent(
        [], user_msg, customer=single_order_customer
    )

    assert is_pending is True
    assert email == "single.order@example.com"
    assert order_id == "single_order_abc123"


def test_customer_00002_latest_order_returns_one_item():
    """
    CONFIRMATION TEST: Customer 00002 actual latest order by purchase timestamp
    is ff89ef7b3952bba5ac06d61c4a79ffbe, which genuinely contains 1 item (Bed Bath & Table).
    """
    customer = get_persona_by_id("DEMO_00002")
    assert customer is not None
    assert customer.total_orders == 9

    tools = build_customer_tools(customer)
    details_tool = next(t for t in tools if t.name == "get_my_order_details")

    # Calling without order_id resolves to the customer's actual latest order
    output = details_tool.invoke({})
    assert "ff89ef7b3952bba5ac06d61c4a79ffbe" in output
    assert "Bed Bath & Table" in output
    # Must contain exactly 1 item in breakdown
    assert "Item #1:" in output
    assert "Item #2:" not in output


def test_customer_00002_specific_order_returns_two_items():
    """
    CONFIRMATION TEST: Customer 00002 older sample order 826b47e4cd7bba4e4c6fa5485f898b74
    genuinely contains 2 items: Home Construction (R$239.90) and Furniture & Decor (R$97.00).
    """
    customer = get_persona_by_id("DEMO_00002")
    tools = build_customer_tools(customer)
    details_tool = next(t for t in tools if t.name == "get_my_order_details")

    specific_order_id = "826b47e4cd7bba4e4c6fa5485f898b74"
    output = details_tool.invoke({"order_id": specific_order_id})

    assert specific_order_id in output
    assert "Home Construction" in output
    assert "Furniture & Decor" in output
    assert "Item #1:" in output
    assert "Item #2:" in output
    assert "239.90" in output
    assert "97.00" in output


def test_escalation_ticket_payload_includes_order_id():
    """Verify request_human_escalation attaches order_id to ticket reason and return text."""
    customer = get_persona_by_id("DEMO_00001")
    tools = build_escalation_tools(customer)
    esc_tool = next(t for t in tools if t.name == "request_human_escalation")

    result = esc_tool.invoke({
        "reason": "Delivered package was crushed in transit",
        "contact_info": "customer.test@example.com",
        "order_id": "c2213109a2cc0e75d55585b7aaac6d97",
    })

    assert "Escalation Request Created Successfully" in result
    assert "ESC-" in result
    assert "c2213109a2cc0e75d55585b7aaac6d97" in result
    assert "customer.test@example.com" in result
    assert "Affected Order:" in result





