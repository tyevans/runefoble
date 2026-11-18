"""Blackbox frontdoor tests for voice_agent schema permissions (TASK-0558).

Every route drives the public HTTP or WebSocket surface with a signed bearer token.
Roles come from tuples that use schema names only (`campaign#dungeon_master`,
`campaign#player`). A spectator holds no tuple, so the permission check denies it.

Governed by:
- ADR-0001: SpiceDB Zanzibar object-level authorization
- ADR-0014: frontdoor blackbox tests over HTTP and WebSocket
"""

from __future__ import annotations

import asyncio
import base64
import uuid

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.errors import AuthzSchemaError, AuthzUnavailableError
from starlette.websockets import WebSocketDisconnect
from voice_agent.main import app as voice_app

from tests.helpers.audio_synth import generate_pcm_sine
from tests.helpers.spicedb_factory import grant_voice_session, shared_spicedb_client
from tests.helpers.voice_identity import (
    VOICE_SIGNING_ISSUER,
    voice_auth_headers,
    voice_ws_subprotocols,
)

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

DM = "user-dm"
PLAYER = "user-player"
SPECTATOR = "user-spectator"
PCM_B64 = base64.b64encode(generate_pcm_sine(duration_ms=50)).decode("ascii")


@pytest.fixture
def session_id() -> str:
    """A fresh session with one DM and one player. The spectator has no tuple."""
    sid = f"sess-authz-{uuid.uuid4().hex[:8]}"
    asyncio.run(grant_voice_session(sid, dm=DM, players=[PLAYER]))
    return sid


@pytest.fixture
def client() -> TestClient:
    return TestClient(voice_app)


class _StubSpiceDB:
    """Stands in for SpiceDB at the process boundary. Every check raises the given error."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def check_permission(self, *args, **kwargs) -> bool:
        raise self._error


def test_player_cannot_kick_and_dm_can(client, session_id):
    body = {"peer_id": "peer-x", "reason": "mic_spam"}

    denied = client.post(
        f"/api/v1/voice/rooms/{session_id}/kick", headers=voice_auth_headers(PLAYER), json=body
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["required_permission"] == "session.control"

    allowed = client.post(
        f"/api/v1/voice/rooms/{session_id}/kick", headers=voice_auth_headers(DM), json=body
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["kicked_by"] == DM


def test_raw_bearer_value_is_not_an_identity(client, session_id):
    token = VOICE_SIGNING_ISSUER.mint(DM)

    res = client.post(
        f"/api/v1/voice/rooms/{session_id}/kick",
        headers={"Authorization": token},
        json={"peer_id": "peer-x"},
    )

    assert res.status_code == 401, res.text
    assert res.headers.get("WWW-Authenticate") == "Bearer"


def test_aec_benchmark_requires_a_principal(client):
    res = client.post("/api/v1/voice/aec/benchmark", json={"session_id": "sess-none"})

    assert res.status_code == 401, res.text


def test_aec_benchmark_requires_session_control(client, session_id):
    body = {
        "session_id": session_id,
        "reference_audio_base64": PCM_B64,
        "microphone_audio_base64": PCM_B64,
    }

    player = client.post(
        "/api/v1/voice/aec/benchmark", headers=voice_auth_headers(PLAYER), json=body
    )
    assert player.status_code == 403, player.text

    dm = client.post("/api/v1/voice/aec/benchmark", headers=voice_auth_headers(DM), json=body)
    assert dm.status_code == 200, dm.text


def test_spectator_cannot_synthesize_speech(client, session_id):
    res = client.post(
        "/api/v1/voice/synthesize",
        headers=voice_auth_headers(SPECTATOR),
        json={"text": "Hello traveler", "session_id": session_id, "speaker_id": SPECTATOR},
    )

    assert res.status_code == 403, res.text
    assert res.json()["detail"]["required_permission"] == "session.participate"


def test_principal_cannot_act_for_another_speaker_without_control(client, session_id):
    res = client.post(
        "/api/v1/voice/dsp/apply",
        headers=voice_auth_headers(PLAYER),
        json={
            "session_id": session_id,
            "speaker_id": DM,
            "audio_base64": PCM_B64,
            "filters": ["whisper"],
        },
    )

    assert res.status_code == 403, res.text
    assert res.json()["detail"]["required_permission"] == "session.control"


def test_dm_may_act_for_a_participating_speaker(client, session_id):
    res = client.post(
        "/api/v1/voice/dsp/apply",
        headers=voice_auth_headers(DM),
        json={
            "session_id": session_id,
            "speaker_id": PLAYER,
            "audio_base64": PCM_B64,
            "filters": ["whisper"],
        },
    )

    assert res.status_code == 200, res.text


def test_duplex_websocket_refuses_a_speaker_the_principal_may_not_act_for(session_id):
    client = TestClient(voice_app)

    with (
        pytest.raises(WebSocketDisconnect) as exc,
        client.websocket_connect(
            f"/api/v1/voice/duplex/ws/{session_id}/{DM}",
            subprotocols=voice_ws_subprotocols(PLAYER),
        ) as ws,
    ):
        ws.receive_json()

    assert exc.value.code == 1008


def test_duplex_websocket_admits_the_principal_as_speaker(session_id):
    client = TestClient(voice_app)

    with client.websocket_connect(
        f"/api/v1/voice/duplex/ws/{session_id}/{PLAYER}",
        subprotocols=voice_ws_subprotocols(PLAYER),
    ) as ws:
        assert ws.receive_json()["type"] == "voice_duplex_connected"


def test_stream_frame_naming_another_speaker_closes_the_socket(session_id):
    client = TestClient(voice_app)

    with client.websocket_connect(
        f"/api/v1/voice/stream/ws/{session_id}/{PLAYER}",
        subprotocols=voice_ws_subprotocols(PLAYER),
    ) as ws:
        ws.send_json({"session_id": session_id, "speaker_id": DM, "audio_data": PCM_B64})
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()

    assert exc.value.code == 1008


def test_spicedb_outage_maps_to_503_with_a_stable_body(client, session_id):
    stub = _StubSpiceDB(AuthzUnavailableError("UNAVAILABLE: connection refused to spicedb:50051"))

    with shared_spicedb_client(stub):
        res = client.post(
            f"/api/v1/voice/rooms/{session_id}/kick",
            headers=voice_auth_headers(DM),
            json={"peer_id": "peer-x"},
        )

    assert res.status_code == 503, res.text
    assert res.json() == {"error": "authorization_unavailable"}
    assert "spicedb" not in res.text


def test_spicedb_schema_mismatch_maps_to_500_with_an_error_id(client, session_id):
    stub = _StubSpiceDB(AuthzSchemaError("FAILED_PRECONDITION: unknown permission 'owner'"))

    with shared_spicedb_client(stub):
        res = client.post(
            f"/api/v1/voice/rooms/{session_id}/kick",
            headers=voice_auth_headers(DM),
            json={"peer_id": "peer-x"},
        )

    assert res.status_code == 500, res.text
    body = res.json()
    assert body["error"] == "authorization_schema_error"
    assert uuid.UUID(body["error_id"])
    assert "FAILED_PRECONDITION" not in res.text
