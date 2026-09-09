"""
Conversation Memory Store.
Maintains multi-turn conversation history per session/conversation ID in memory.
"""

from typing import Dict, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# In-memory dictionary holding conversation histories
_CONVERSATION_STORE: Dict[str, List[BaseMessage]] = {}
_MAX_HISTORY_MESSAGES: int = 12  # Rolling window of last 6 complete dialogue turns


def get_conversation_history(conversation_id: str) -> List[BaseMessage]:
    """Retrieves the list of messages for a given conversation ID."""
    return list(_CONVERSATION_STORE.get(conversation_id, []))


def add_message(conversation_id: str, message: BaseMessage) -> None:
    """Appends a message to the conversation history, maintaining the rolling window."""
    if conversation_id not in _CONVERSATION_STORE:
        _CONVERSATION_STORE[conversation_id] = []

    _CONVERSATION_STORE[conversation_id].append(message)
    # Trim to maximum history window to conserve context and tokens
    if len(_CONVERSATION_STORE[conversation_id]) > _MAX_HISTORY_MESSAGES:
        _CONVERSATION_STORE[conversation_id] = _CONVERSATION_STORE[conversation_id][-_MAX_HISTORY_MESSAGES:]


def add_user_message(conversation_id: str, content: str) -> None:
    """Convenience helper to record a human user message."""
    add_message(conversation_id, HumanMessage(content=content))


def add_ai_message(conversation_id: str, content: str) -> None:
    """Convenience helper to record an assistant AI response."""
    add_message(conversation_id, AIMessage(content=content))


def clear_conversation(conversation_id: str) -> bool:
    """Clears all stored history for a conversation ID."""
    if conversation_id in _CONVERSATION_STORE:
        del _CONVERSATION_STORE[conversation_id]
        return True
    return False
