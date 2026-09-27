"""Blackbox TDD tests for OpenPanel Analytics Client and Privacy Scrubbing.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Verifies salted SHA-256 profile anonymization, recursive PII scrubbing,
and asynchronous HTTP transport dispatch to OpenPanel endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import pytest
from runefoble_platform.analytics import (
    OpenPanelClient,
    anonymize_profile_id,
    sanitize_properties,
)


@pytest.fixture
def analytics_client() -> OpenPanelClient:
    return OpenPanelClient(
        endpoint="http://openpanel:3000/api",
        client_id="rf_test_client_id",
        salt="test_salt_analytics_99",
        mock_mode=True,
    )


def test_sanitize_properties_removes_audio_and_transcripts() -> None:
    """Properties with sensitive audio, dialogue, or credential keys must be stripped."""
    dirty: dict[str, Any] = {
        "session_id": "sess-123",
        "audio": b"RIFF...wav",
        "raw_audio": "http://audio/s.wav",
        "audio_bytes": "b64...",
        "transcript": "Cast Fireball",
        "raw_transcript": "raw stt",
        "speech": "speech text",
        "dialogue": "Watch out!",
        "token": "secret_jwt",
        "password": "pass",
        "email": "p@example.com",
        "nested": {"character_name": "Valeros", "transcript": "nested"},
        "safe_int": 42,
    }
    clean = sanitize_properties(dirty)
    assert "session_id" in clean and "safe_int" in clean
    assert clean["nested"] == {"character_name": "Valeros"}

    for key in (
        "audio",
        "raw_audio",
        "audio_bytes",
        "transcript",
        "raw_transcript",
        "speech",
        "dialogue",
        "token",
        "password",
        "email",
    ):
        assert key not in clean


def test_anonymize_profile_id_hashing() -> None:
    """Anonymization must be deterministic with salt, producing consistent hashes."""
    salt, pid = "my_custom_salt_123", "user_valeros_99"
    hash1, hash2 = anonymize_profile_id(pid, salt=salt), anonymize_profile_id(pid, salt=salt)
    assert hash1 == hash2 and hash1 is not None and len(hash1) == 32 and pid not in hash1
    assert hash1 != anonymize_profile_id(pid, salt="other_salt")
    assert anonymize_profile_id(None) is None and anonymize_profile_id("") is None


@pytest.mark.asyncio
async def test_openpanel_client_http_dispatch_with_mock_transport() -> None:
    """Verify OpenPanelClient dispatches HTTP POST requests to configured endpoint."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "ok"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_mock:
        client = OpenPanelClient(
            endpoint="http://openpanel:3000/api",
            client_id="proj_xyz",
            salt="salt_1",
            mock_mode=False,
            http_client=http_mock,
        )
        result = await client.track(
            event_name="session.started",
            properties={"campaign_type": "5e"},
            profile_id="player-1",
        )
        assert result["event"] == "session.started"
        assert len(captured) == 1
        req = captured[0]
        assert str(req.url) == "http://openpanel:3000/api/event"
        assert req.headers["openpanel-client-id"] == "proj_xyz"
        assert req.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_openpanel_client_identify_and_buffer_management() -> None:
    """Verify profile identification dispatch, payload sanitization, and buffer clearing."""
    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json={"success": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_mock:
        client = OpenPanelClient(
            endpoint="http://openpanel:3000/api",
            client_id="proj_xyz",
            salt="salt_ident",
            mock_mode=False,
            http_client=http_mock,
        )
        res = await client.identify(
            profile_id=uuid4(),
            traits={"name": "Krynn", "transcript": "secret speech", "level": 5},
        )
        assert res["traits"]["name"] == "Krynn"
        assert "transcript" not in res["traits"]
        assert len(captured) == 1
        assert str(captured[0].url) == "http://openpanel:3000/api/profile"

        assert len(client.recorded_events) == 1
        client.clear()
        assert len(client.recorded_events) == 0
        await client.close()


@pytest.mark.asyncio
async def test_openpanel_client_fast_failure_and_error_resilience() -> None:
    """Network errors during HTTP dispatch must fail gracefully without throwing."""

    def failing_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused by test mock")

    async with httpx.AsyncClient(transport=httpx.MockTransport(failing_handler)) as http_mock:
        client = OpenPanelClient(
            endpoint="http://unavailable-openpanel:3000/api",
            client_id="proj_fail",
            mock_mode=False,
            http_client=http_mock,
        )
        track_res = await client.track(event_name="test.event", properties={"key": "val"})
        ident_res = await client.identify(profile_id="p-1", traits={"trait": 1})
        assert track_res["event"] == "test.event"
        assert ident_res["profile_id"] is not None
        assert len(client.recorded_events) == 2
        await client.close()
