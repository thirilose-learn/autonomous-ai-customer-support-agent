"""
Free Hosted LLM Model Factory.
Initializes ChatGroq backed by Groq Cloud Free Developer Tier.
Supports Llama 3.3 70B Versatile and Llama 3.1 8B Instant with zero cost.
"""

from typing import Optional
from langchain_groq import ChatGroq
from app.core.config import settings


def get_chat_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: int = 2,
) -> ChatGroq:
    """
    Constructs an authenticated ChatGroq instance.
    Defaults to settings.GROQ_MODEL (llama-3.3-70b-versatile).
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not configured in backend/.env. "
            "Please obtain a free developer key from https://console.groq.com (no credit card required) "
            "and add it to backend/.env as GROQ_API_KEY=gsk_..."
        )

    selected_model = model or settings.GROQ_MODEL
    selected_temp = temperature if temperature is not None else settings.GROQ_TEMPERATURE

    return ChatGroq(
        model=selected_model,
        temperature=selected_temp,
        groq_api_key=api_key,
        max_retries=max_retries,
    )
