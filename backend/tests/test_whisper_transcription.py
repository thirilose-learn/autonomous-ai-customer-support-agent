"""
Unit and Integration Tests for Speech-to-Text Whisper Transcription Endpoint.
Validates:
1. Authentication requirement on /api/v1/chat/transcribe.
2. Empty or too-short audio rejection (HTTP 400).
3. Successful Whisper transcription with Groq client mock (HTTP 200).
4. Graceful handling of upstream Groq errors (HTTP 500).
"""

import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_transcribe_unauthenticated_rejected():
    """Verify that requests without a valid session token are rejected."""
    resp = client.post(
        "/api/v1/chat/transcribe",
        content=b"dummy audio content longer than 64 bytes" * 5,
        headers={"Content-Type": "audio/webm"},
    )
    assert resp.status_code in [401, 403]


def test_transcribe_empty_audio_rejected():
    """Verify that empty or tiny audio recordings are rejected with HTTP 400."""
    # Login to obtain a valid demo customer token
    auth_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]

    # Post empty audio bytes
    resp = client.post(
        "/api/v1/chat/transcribe",
        content=b"too short",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
    )
    assert resp.status_code == 400
    assert "empty or too short" in resp.json()["detail"].lower()


def test_transcribe_successful_with_mock():
    """Verify successful speech recognition returns structured transcription text."""
    auth_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = auth_resp.json()["access_token"]

    # Mock groq audio transcription
    mock_transcription = MagicMock()
    mock_transcription.text = "Where is my recent order?"

    with patch("groq.Groq") as MockGroq:
        mock_instance = MagicMock()
        mock_instance.audio.transcriptions.create.return_value = mock_transcription
        MockGroq.return_value = mock_instance

        resp = client.post(
            "/api/v1/chat/transcribe",
            content=b"RIFF" + b"\x00" * 200,  # Mock audio payload > 64 bytes
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/wav",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Where is my recent order?"
        assert data["language"] == "en"

        mock_instance.audio.transcriptions.create.assert_called_once()


def test_transcribe_upstream_error_handled_gracefully():
    """Verify that Groq transcription exceptions return a clean HTTP 500 error."""
    auth_resp = client.post(
        "/api/v1/auth/select-persona",
        json={"demo_customer_id": "DEMO_00001"},
    )
    token = auth_resp.json()["access_token"]

    with patch("groq.Groq") as MockGroq:
        mock_instance = MagicMock()
        mock_instance.audio.transcriptions.create.side_effect = RuntimeError("Groq API rate limit exceeded")
        MockGroq.return_value = mock_instance

        resp = client.post(
            "/api/v1/chat/transcribe",
            content=b"RIFF" + b"\x00" * 200,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/wav",
            },
        )
        assert resp.status_code == 500
        assert "Whisper transcription failed" in resp.json()["detail"]
