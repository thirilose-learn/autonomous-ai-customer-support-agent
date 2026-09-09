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
                fallback_llm = get_chat_llm(model=settings.GROQ_FALLBACK_MODEL).bind_tools(all_tools)
                ai_msg = fallback_llm.invoke(active_messages)
            else:
                raise

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

    # If the loop ended after tool calls without final message, invoke one last time for synthesis
    if not final_response_text:
        try:
            synthesis_msg = llm_with_tools.invoke(active_messages)
            final_response_text = synthesis_msg.content or ""
        except Exception as err:
            logger.error(f"Error during final response synthesis: {err}")
            final_response_text = "I have processed your request based on your account records."

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
