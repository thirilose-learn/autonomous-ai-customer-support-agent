"""
Chat API Endpoint.
Exposes conversational customer support powered by the Level 5 Autonomous AI Agent.
Enforces authentication and customer isolation via CustomerContext.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from app.api.deps import get_current_customer
from app.schemas.session import CustomerContext
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatResetResponse
from app.agents.agent import run_customer_agent_turn
from app.agents.memory import clear_conversation

router = APIRouter()


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send message to AI Support Agent",
    description="Processes a user inquiry through the customer-scoped AI agent with tool calling and RAG retrieval.",
)
def send_chat_message(
    payload: ChatMessageRequest,
    customer: CustomerContext = Depends(get_current_customer),
) -> ChatMessageResponse:
    """
    Submits a customer message to the AI agent.
    Binds the agent strictly to the authenticated CustomerContext.
    """
    conv_id = payload.conversation_id or f"session-{customer.demo_customer_id}"
    try:
        response = run_customer_agent_turn(
            customer=customer,
            user_message=payload.message,
            conversation_id=conv_id,
        )
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent resolution failed: {str(exc)}",
        )


@router.post(
    "/reset",
    response_model=ChatResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset conversation history",
)
def reset_chat_history(
    payload: ChatMessageRequest,
    customer: CustomerContext = Depends(get_current_customer),
) -> ChatResetResponse:
    """
    Clears the multi-turn memory buffer for the specified or default customer session.
    """
    conv_id = payload.conversation_id or f"session-{customer.demo_customer_id}"
    clear_conversation(conv_id)
    return ChatResetResponse(
        status="success",
        message=f"Conversation memory cleared for session {conv_id}",
        conversation_id=conv_id,
    )
