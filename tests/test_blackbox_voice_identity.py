"""Blackbox tests: voice_agent verifies identity on every HTTP and WebSocket route (TASK-0530).

Governed by ADR-0015 decision (c) and Hard Invariant 1. Tests use only public HTTP routes
and WebSocket handshakes. Tokens come from signing issuers. Nothing reads private state.
"""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from starlette.websockets import WebSocketDisconnect
from voice_agent.main import app as voice_app

from tests.helpers.audio_synth import generate_synthetic_audio
from tests.helpers.voice_grants import grant_voice_session
from tests.helpers.voice_identity import VOICE_SIGNING_ISSUER, voice_auth_headers

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

SESSION_ID = "sess-identity-voice"
FORGED_ISSUER = SigningTestIssuer()
WS_CLOSE_POLICY_VIOLATION = 1008

PCM_B64 = base64.b64encode(generate_synthetic_audio(duration_sec=0.04, sample_rate=16000)).decode(
    "ascii"
)


def _kick_body() -> dict:
    return {"peer_id": "peer-target", "reason": "mic_spam"}


def _modulate_body() -> dict:
    return {"session_id": SESSION_ID, "preset_name": "Goblin Skulker", "audio_base64": PCM_B64}


# (method, path, json body) for every mutating or session-scoped HTTP route in voice_agent.
GUARDED_HTTP_ROUTES: list[tuple[str, str, Callable[[], dict] | None]] = [
    ("POST", f"/api/v1/voice/rooms/{SESSION_ID}/kick", _kick_body),
    ("GET", f"/api/v1/voice/rooms/{SESSION_ID}", None),
    ("POST", "/api/v1/voice/modulate", _modulate_body),
    ("GET", "/api/v1/voice/presets", None),
    ("POST", "/api/v1/voice/dsp/condition", lambda: {"text": "Hello", "filters": ["drunk"]}),
    ("POST", "/api/v1/voice/dsp/apply", lambda: {"audio_base64": PCM_B64, "filter": "whisper"}),
    ("POST", "/api/v1/voice/tts", lambda: {"text": "Hello traveler", "persona": "narrator"}),
    ("POST", "/api/v1/voice/synthesize", lambda: {"text": "Hello traveler"}),
    ("POST", "/api/v1/voice/transcribe", lambda: {"text": "Hello"}),
    ("POST", "/api/v1/voice/stream/chunk", lambda: {"session_id": "s", "speaker_id": "p"}),
    ("POST", "/api/v1/voice/duplex/playback/start", lambda: {}),
    ("GET", "/api/v1/voice/duplex/status/sess-x", None),
    ("POST", "/api/v1/voice/aec/benchmark", lambda: {}),
    ("POST", "/api/v1/voice/filters/barge-in/evaluate", lambda: {}),
    ("POST", f"/api/v1/voice/streams/{SESSION_ID}/report", lambda: {}),
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(voice_app)


@pytest.fixture
def spicedb():
    """The per-test strict SpiceDB mock that every voice route reads through the factory."""
    return get_spicedb_client()


def _send(client: TestClient, method: str, path: str, body: Callable[[], dict] | None, headers):
    kwargs = {"headers": headers}
    if body is not None and method == "POST":
        kwargs["json"] = body()
    return client.request(method, path, **kwargs)


@pytest.mark.parametrize(("method", "path", "body"), GUARDED_HTTP_ROUTES)
def test_http_route_refuses_request_without_bearer(client, method, path, body):
    res = _send(client, method, path, body, headers=None)

    assert res.status_code == 401, res.text
    assert res.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.parametrize(("method", "path", "body"), GUARDED_HTTP_ROUTES)
def test_http_route_refuses_garbage_bearer(client, method, path, body):
    res = _send(client, method, path, body, headers={"Authorization": "Bearer not-a-jwt"})

    assert res.status_code == 401, res.text


@pytest.mark.parametrize(("method", "path", "body"), GUARDED_HTTP_ROUTES)
def test_http_route_refuses_token_from_untrusted_issuer(client, method, path, body):
    forged = FORGED_ISSUER.mint("user-dm")

    res = _send(client, method, path, body, headers={"Authorization": f"Bearer {forged}"})

    assert res.status_code == 401, res.text


@pytest.mark.parametrize(("method", "path", "body"), GUARDED_HTTP_ROUTES)
def test_http_route_refuses_legacy_identity_headers(client, method, path, body):
    res = _send(
        client,
        method,
        path,
        body,
        headers={"X-User-Id": "dm-evelyn", "Authorization": "dm-evelyn"},
    )

    assert res.status_code == 401, res.text


def test_health_and_manifest_stay_public(client):
    assert client.get("/ui/manifest").status_code == 200


def test_forged_x_user_id_does_not_change_the_kick_subject(client, spicedb):
    """A stranger with a valid token cannot borrow the DM's identity through X-User-Id."""
    _grant_control(spicedb, "dm-evelyn")
    headers = {**voice_auth_headers("stranger-token"), "X-User-Id": "dm-evelyn"}

    res = client.post(f"/api/v1/voice/rooms/{SESSION_ID}/kick", headers=headers, json=_kick_body())

    assert res.status_code == 403, res.text
    assert res.json()["detail"]["subject"] == "user:stranger-token"


def test_forged_x_user_id_does_not_grant_the_modulate_route(client, spicedb):
    _grant_control(spicedb, "dm-evelyn")
    headers = {**voice_auth_headers("stranger-token"), "X-User-Id": "dm-evelyn"}

    res = client.post("/api/v1/voice/modulate", headers=headers, json=_modulate_body())

    assert res.status_code == 403, res.text


def test_token_subject_drives_the_modulate_permission(client, spicedb):
    _grant_control(spicedb, "dm-evelyn")

    res = client.post(
        "/api/v1/voice/modulate",
        headers={**voice_auth_headers("dm-evelyn"), "X-User-Id": "stranger-token"},
        json=_modulate_body(),
    )

    assert res.status_code == 200, res.text


def _grant_control(spicedb, user_id: str) -> None:
    """Make `user_id` the DM of the session. voice_agent has no grant frontdoor, so tuples are written."""
    asyncio.run(grant_voice_session(SESSION_ID, dm=user_id))


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/voice/duplex/ws/{SESSION_ID}/spk-1",
        f"/api/v1/voice/stream/ws/{SESSION_ID}/spk-1",
    ],
)
def test_websocket_refuses_handshake_without_bearer_subprotocol(path):
    client = TestClient(voice_app)

    with (
        pytest.raises(WebSocketDisconnect) as exc,
        client.websocket_connect(path, subprotocols=["runefoble.v1"]),
    ):
        pass

    assert exc.value.code == WS_CLOSE_POLICY_VIOLATION


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/voice/duplex/ws/{SESSION_ID}/spk-1",
        f"/api/v1/voice/stream/ws/{SESSION_ID}/spk-1",
    ],
)
def test_websocket_refuses_forged_or_garbage_bearer(path):
    client = TestClient(voice_app)
    forged = FORGED_ISSUER.mint("user-dm")

    for token in (forged, "not-a-jwt"):
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(
                path, subprotocols=["runefoble.v1", f"runefoble.bearer.{token}"]
            ),
        ):
            pass
        assert exc.value.code == WS_CLOSE_POLICY_VIOLATION


def test_websocket_refuses_token_in_query_string():
    client = TestClient(voice_app)
    token = VOICE_SIGNING_ISSUER.mint("user-dm")

    with (
        pytest.raises(WebSocketDisconnect) as exc,
        client.websocket_connect(
            f"/api/v1/voice/duplex/ws/{SESSION_ID}/spk-1?token={token}",
            subprotocols=["runefoble.v1"],
        ),
    ):
        pass

    assert exc.value.code == WS_CLOSE_POLICY_VIOLATION


def test_duplex_websocket_accepts_valid_bearer_subprotocol():
    asyncio.run(grant_voice_session(SESSION_ID, dm="user-dm", players=["spk-1"]))
    client = TestClient(voice_app)
    token = VOICE_SIGNING_ISSUER.mint("user-dm")

    with client.websocket_connect(
        f"/api/v1/voice/duplex/ws/{SESSION_ID}/spk-1",
        subprotocols=["runefoble.v1", f"runefoble.bearer.{token}"],
    ) as ws:
        assert ws.accepted_subprotocol == "runefoble.v1"
        assert ws.receive_json()["type"] == "voice_duplex_connected"


def test_stream_websocket_accepts_valid_bearer_subprotocol():
    client = TestClient(voice_app)
    token = VOICE_SIGNING_ISSUER.mint("user-dm")

    with client.websocket_connect(
        f"/api/v1/voice/stream/ws/{SESSION_ID}/spk-1",
        subprotocols=["runefoble.v1", f"runefoble.bearer.{token}"],
    ) as ws:
        assert ws.accepted_subprotocol == "runefoble.v1"
