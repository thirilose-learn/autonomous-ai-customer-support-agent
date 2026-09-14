"""
Agent Coordinator and Execution Engine.
Orchestrates authenticated CustomerContext, tool execution loop, multi-turn memory,
and free hosted Groq Cloud LLM inference.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.core.config import settings
from app.schemas.session import CustomerContext
from app.schemas.chat import ChatMessageResponse, ToolExecutionRecord
from app.agents.llm import get_chat_llm
from app.agents.prompts import get_system_prompt
from app.agents.memory import (
    get_conversation_history,
    add_user_message,
    add_ai_message,
)
from app.agents.tools.customer_tools import build_customer_tools
from app.agents.tools.policy_tool import get_policy_tools
from app.agents.tools.escalation_tool import build_escalation_tools

logger = logging.getLogger(__name__)


def classify_intent(tools_executed: List[str], user_message: str) -> str:
    """Classifies primary intent based on tools executed and user prompt."""
    if "request_human_escalation" in tools_executed:
        return "ESCALATION"
    if "get_my_orders" in tools_executed or "get_my_order_details" in tools_executed or "get_my_payment_details" in tools_executed:
        return "ORDER_INQUIRY"
    if "search_policy_knowledge_base" in tools_executed:
        return "POLICY_RAG"

    lower = user_message.lower()
    if any(w in lower for w in ["return", "refund", "cancel", "warranty", "ship", "policy"]):
        return "POLICY_RAG"
    if any(w in lower for w in ["order", "package", "deliver", "track", "buy", "purchase"]):
        return "ORDER_INQUIRY"
    if any(w in lower for w in ["human", "agent", "manager", "representative", "help"]):
        return "GENERAL_SUPPORT"
    return "GENERAL_CONVERSATION"


def run_customer_agent_turn(
    customer: CustomerContext,
    user_message: str,
    conversation_id: str,
) -> ChatMessageResponse:
    """
    Executes a single conversational agent turn grounded in the customer's authenticated context.
    """
    start_time = time.perf_counter()

    # 1. Build session-bound toolset
    customer_tools = build_customer_tools(customer)
    policy_tools = get_policy_tools()
    escalation_tools = build_escalation_tools(customer)
    all_tools = customer_tools + policy_tools + escalation_tools
    tool_map: Dict[str, BaseTool] = {t.name: t for t in all_tools}

    # 2. Retrieve multi-turn conversation history
    history = get_conversation_history(conversation_id)

    # 3. Assemble prompt messages
    system_msg = SystemMessage(content=get_system_prompt(customer))
    user_msg = HumanMessage(content=user_message)
    active_messages = [system_msg] + history + [user_msg]

    # Check if this turn is providing contact info for a pending escalation / supervisor review
    from app.services.escalation_policy import (
        detect_pending_escalation_intent,
        get_previous_order_from_history,
    )
    is_pending_esc, esc_email, esc_phone, esc_reason, esc_order_id = detect_pending_escalation_intent(
        history, user_message, customer=customer
    )
    if is_pending_esc:
        contact_val = esc_email or esc_phone
        order_clause = f" for order '{esc_order_id}'" if esc_order_id else ""
        order_arg_note = f", order_id='{esc_order_id}'" if esc_order_id else ""
        active_messages.append(
            SystemMessage(
                content=(
                    f"[IMMEDIATE ACTION DIRECTIVE]: The customer has provided verified contact information ('{contact_val}') "
                    f"for an ongoing issue requiring supervisor review/escalation ('{esc_reason}'){order_clause}. "
                    f"You MUST call `request_human_escalation` right now with contact_info='{contact_val}'{order_arg_note} to create their ticket. "
                    f"Do NOT claim to send emails or labels yourself."
                )
            )
        )
    elif esc_reason and (esc_email or esc_phone) and customer and getattr(customer, "total_orders", 0) > 1:
        # Substantive issue + contact exist, but order context is unconfirmed/missing for multi-order customer
        prev_oid = get_previous_order_from_history(history)
        if prev_oid:
            active_messages.append(
                SystemMessage(
                    content=(
                        f"[ORDER CLARIFICATION DIRECTIVE]: The customer reported an order issue ('{esc_reason}') with contact info, "
                        f"and an order ('{prev_oid}') was discussed previously in the conversation. "
                        f"However, the customer has NOT confirmed whether this issue concerns that order or a different order. "
                        f"You MUST NOT call `request_human_escalation` yet. "
                        f"You MUST ask: 'Is this regarding the order we just discussed, or a different order? If it's a different order, please provide the order ID.' "
                        f"Wait for the customer's answer."
                    )
                )
            )
        else:
            active_messages.append(
                SystemMessage(
                    content=(
                        "[ORDER CLARIFICATION DIRECTIVE]: The customer has multiple orders and has reported an order issue, "
                        "but has not specified which order is affected. "
                        "You MUST NOT call `request_human_escalation` yet. "
                        "Ask the customer which order was affected by providing the order ID, approximate order date, or product/item name."
                    )
                )
            )

    # 4. Initialize LLM with tool binding
    try:
        llm = get_chat_llm(model=settings.GROQ_MODEL)
    except Exception as exc:
        logger.warning(f"Failed to initialize primary model, trying fallback: {exc}")
        llm = get_chat_llm(model=settings.GROQ_FALLBACK_MODEL)

    llm_with_tools = llm.bind_tools(all_tools)

    tools_executed: List[str] = []
    tool_records: List[ToolExecutionRecord] = []

    # 5. Agent Tool Execution Loop (up to 3 iterations for multi-step reasoning)
    max_tool_iterations = 3
    final_response_text = ""

    for iteration in range(max_tool_iterations):
        try:
            ai_msg = llm_with_tools.invoke(active_messages)
        except Exception as exc:
            logger.error(f"Error during LLM invocation turn: {exc}")
            # Try once with fallback model if primary hit a rate limit or failure
            if settings.GROQ_FALLBACK_MODEL and settings.GROQ_FALLBACK_MODEL != settings.GROQ_MODEL:
                try:
                    fallback_llm = get_chat_llm(model=settings.GROQ_FALLBACK_MODEL).bind_tools(all_tools)
                    ai_msg = fallback_llm.invoke(active_messages)
                except Exception as fb_exc:
                    logger.error(f"Fallback model also failed: {fb_exc}")
                    final_response_text = (
                        "I am experiencing a temporary service delay with our AI system. "
                        "Please try your inquiry again in a moment, or request a supervisor review if this is urgent."
                    )
                    break
            else:
                final_response_text = (
                    "I am experiencing a temporary service delay with our AI system. "
                    "Please try your inquiry again in a moment, or request a supervisor review if this is urgent."
                )
                break

        # Check if the model generated tool calls
        tool_calls = getattr(ai_msg, "tool_calls", []) or []
        if not tool_calls:
            # Model produced natural language output directly
            final_response_text = ai_msg.content or ""
            break

        # Process each tool call
        active_messages.append(ai_msg)
        for tc in tool_calls:
            t_name = tc.get("name")
            t_args = tc.get("args") or {}
            t_id = tc.get("id") or f"call_{len(tools_executed)}"

            tools_executed.append(t_name)
            tool_fn = tool_map.get(t_name)

            if t_name == "request_human_escalation":
                from app.services.escalation_policy import extract_contact_info, is_generic_human_request
                contact_arg = t_args.get("contact_info", "")
                if not contact_arg or not str(contact_arg).strip():
                    conv_text = " ".join([str(m.content) for m in history if hasattr(m, "content")] + [user_message])
                    hist_email, hist_phone = extract_contact_info(conv_text)
                    if hist_email:
                        t_args["contact_info"] = hist_email
                    elif hist_phone:
                        t_args["contact_info"] = hist_phone
                if esc_reason and (not t_args.get("reason") or is_generic_human_request(t_args.get("reason", ""))):
                    t_args["reason"] = esc_reason
                if esc_order_id and not t_args.get("order_id"):
                    t_args["order_id"] = esc_order_id

            if tool_fn:
                try:
                    tool_output = tool_fn.invoke(t_args)
                    success = True
                except Exception as t_err:
                    tool_output = f"Error executing tool {t_name}: {str(t_err)}"
                    success = False
            else:
                tool_output = f"Tool '{t_name}' is not recognized."
                success = False

            output_str = str(tool_output)
            tool_records.append(
                ToolExecutionRecord(
                    tool_name=t_name,
                    arguments=t_args,
                    success=success,
                    output_preview=output_str[:200] + ("..." if len(output_str) > 200 else ""),
                )
            )

            # Append ToolMessage back to conversation sequence
            active_messages.append(
                ToolMessage(
                    content=output_str,
                    tool_call_id=t_id,
                    name=t_name,
                )
            )

    # Deterministic enforcement: If escalation was pending with valid contact, but model failed to call the tool
    if is_pending_esc and "request_human_escalation" not in tools_executed:
        esc_tool = tool_map.get("request_human_escalation")
        if esc_tool:
            contact_val = esc_email or esc_phone
            try:
                esc_output = esc_tool.invoke({
                    "reason": esc_reason or "Customer requested supervisor review for unresolvable issue",
                    "contact_info": contact_val,
                    "urgency": "normal",
                    "order_id": esc_order_id,
                })
                tools_executed.append("request_human_escalation")
                tool_records.append(
                    ToolExecutionRecord(
                        tool_name="request_human_escalation",
                        arguments={"reason": esc_reason, "contact_info": contact_val, "order_id": esc_order_id},
                        success=True,
                        output_preview=str(esc_output)[:200],
                    )
                )
                active_messages.append(
                    ToolMessage(
                        content=str(esc_output),
                        tool_call_id=f"auto_call_{len(tools_executed)}",
                        name="request_human_escalation",
                    )
                )
                # Clear final_response_text to force synthesis with tool result
                final_response_text = ""
            except Exception as e_err:
                logger.error(f"Error in automatic escalation fallback: {e_err}")

    # If the loop ended after tool calls without final message, invoke one last time for synthesis
    if not final_response_text or not final_response_text.strip():
        synthesis_directive = SystemMessage(
            content="Please formulate a clear, helpful customer-facing response in English summarizing the account records retrieved above. Do NOT call any tools."
        )
        synthesis_messages = active_messages + [synthesis_directive]
        try:
            # Use unbound llm (WITHOUT tools) to guarantee a natural language response
            synthesis_msg = llm.invoke(synthesis_messages)
            final_response_text = synthesis_msg.content or ""
        except Exception as err:
            logger.warning(f"Primary model error during final response synthesis: {err}, trying fallback model")
            try:
                if settings.GROQ_FALLBACK_MODEL and settings.GROQ_FALLBACK_MODEL != settings.GROQ_MODEL:
                    fallback_synthesis_llm = get_chat_llm(model=settings.GROQ_FALLBACK_MODEL)
                    synthesis_msg = fallback_synthesis_llm.invoke(synthesis_messages)
                    final_response_text = synthesis_msg.content or ""
            except Exception as fb_err:
                logger.error(f"Fallback model also failed during synthesis: {fb_err}")

        # Deterministic guarantee: Never return empty text when tools were executed
        if not final_response_text or not final_response_text.strip():
            if tool_records:
                summary_parts = []
                for rec in tool_records:
                    if rec.success and rec.output_preview:
                        summary_parts.append(rec.output_preview)
                if summary_parts:
                    final_response_text = (
                        f"Here is the verified information from your account records:\n\n"
                        + "\n\n".join(summary_parts[:3])
                    )
                else:
                    final_response_text = (
                        "I checked your account records, but could not find matching information for this inquiry. "
                        "Please provide your specific Order ID or contact support if you need further assistance."
                    )
            else:
                final_response_text = (
                    "I checked your account records, but could not find matching information for this inquiry. "
                    "Please provide your specific Order ID or contact support if you need further assistance."
                )

    # Guardrail against hallucinated email / label generation
    import re
    hallucination_patterns = [
        (r"(?i)I['’]ll generate a (?:prepaid )?return[ -]shipping label and send it[^\.\n]*[\.\n]",
         "A human supervisor will review your case and provide return-shipping documentation if approved. "),
        (r"(?i)I['’]m initiating the return[ -]label email now[^\.\n]*[\.\n]",
         "Our human support team will follow up directly with your return instructions. "),
        (r"(?i)I will generate a (?:prepaid )?return label[^\.\n]*[\.\n]",
         "Our support team will handle return shipping label generation upon review. "),
        (r"(?i)I(?:'ve| have) sent an? (?:confirmation )?email[^\.\n]*[\.\n]",
         "Your contact details have been attached to the ticket for our human support team to follow up. "),
        (r"(?i)An? (?:confirmation )?email has been sent[^\.\n]*[\.\n]",
         "Your contact details have been attached to the ticket for human follow-up. "),
    ]
    for pattern, replacement in hallucination_patterns:
        final_response_text = re.sub(pattern, replacement, final_response_text)

    # Safety guarantee: If escalation tool was executed and produced a ticket ID, ensure the ticket ID is in the response
    if "request_human_escalation" in tools_executed:
        for rec in tool_records:
            if rec.tool_name == "request_human_escalation" and rec.success:
                match = re.search(r"ESC-[A-F0-9]{8}", rec.output_preview or "")
                if match:
                    t_id = match.group(0)
                    if t_id not in final_response_text:
                        final_response_text += f"\n\n**Escalation Reference**: Your case has been logged under Ticket ID **{t_id}**."

    # 6. Record turn in multi-turn memory
    add_user_message(conversation_id, user_message)
    add_ai_message(conversation_id, final_response_text)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    intent = classify_intent(tools_executed, user_message)

    return ChatMessageResponse(
        response=final_response_text,
        intent=intent,
        tools_executed=tools_executed,
        tool_details=tool_records,
        customer=customer,
        conversation_id=conversation_id,
        latency_ms=elapsed_ms,
    )
