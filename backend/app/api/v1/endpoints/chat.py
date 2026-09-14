"""
Chat API Endpoint.
Exposes conversational customer support powered by the Level 5 Autonomous AI Agent.
Enforces authentication and customer isolation via CustomerContext.
"""

import logging
from fastapi import APIRouter, Depends, status, HTTPException, Request
from app.api.deps import get_current_customer
from app.schemas.session import CustomerContext
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatResetResponse,
    AudioTranscriptionResponse,
)
from app.agents.agent import run_customer_agent_turn
from app.agents.memory import clear_conversation
from app.core.config import settings

logger = logging.getLogger(__name__)

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
    # Enforce strict per-persona isolation for conversation memory
    if payload.conversation_id:
        if payload.conversation_id.startswith(f"{customer.demo_customer_id}:"):
            conv_id = payload.conversation_id
        else:
            conv_id = f"{customer.demo_customer_id}:{payload.conversation_id}"
    else:
        conv_id = f"session-{customer.demo_customer_id}"

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
    if payload.conversation_id:
        if payload.conversation_id.startswith(f"{customer.demo_customer_id}:"):
            conv_id = payload.conversation_id
        else:
            conv_id = f"{customer.demo_customer_id}:{payload.conversation_id}"
    else:
        conv_id = f"session-{customer.demo_customer_id}"

    clear_conversation(conv_id)
    return ChatResetResponse(
        status="success",
        message=f"Conversation memory cleared for session {conv_id}",
        conversation_id=conv_id,
    )


@router.post(
    "/transcribe",
    response_model=AudioTranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe speech to text via Whisper",
    description="Transcribes audio speech input into text using Whisper via Groq Cloud API.",
)
async def transcribe_audio(
    request: Request,
    customer: CustomerContext = Depends(get_current_customer),
) -> AudioTranscriptionResponse:
    """
    Receives raw audio bytes (WebM, WAV, etc.) from the customer chat interface,
    calls Whisper via Groq API, and returns transcribed text.
    """
    audio_bytes = await request.body()
    if not audio_bytes or len(audio_bytes) < 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio recording was empty or too short. Please speak clearly and try again.",
        )

    raw_content_type = request.headers.get("content-type", "audio/webm")
    content_type = raw_content_type.split(";")[0].strip() or "audio/webm"

    ext_map = {
        "audio/webm": "webm",
        "audio/wav": "wav",
        "audio/wave": "wav",
        "audio/x-wav": "wav",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/ogg": "ogg",
        "audio/m4a": "m4a",
        "audio/mp4": "mp4",
    }
    ext = ext_map.get(content_type, "webm")
    filename = f"speech_input.{ext}"

    try:
        from groq import Groq
        groq_client = Groq(api_key=settings.GROQ_API_KEY)
        transcription = groq_client.audio.transcriptions.create(
            file=(filename, audio_bytes, content_type),
            model=settings.GROQ_WHISPER_MODEL,
            prompt="Customer support inquiry about orders, returns, refunds, deliveries, or store policies.",
            response_format="json",
            language="en",
            temperature=0.0,
        )
        text = (transcription.text or "").strip()
        return AudioTranscriptionResponse(
            text=text,
            language="en",
        )
    except Exception as exc:
        logger.error(f"Whisper transcription failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Whisper transcription failed: {str(exc)}",
        )

