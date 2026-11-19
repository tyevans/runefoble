"""Blackbox tests for the audio stream WebSocket frame contract (TASK-0915).

The socket path names the session and the speaker. The query names the campaign and the
speaker display name. A missing value is refused: the socket sends an error frame and closes
with 1008. No default id fills the gap. A JSON frame that cannot be parsed gets an
`INVALID_FRAME` error frame, and the socket stays open.
"""

from __future__ import annotations

import asyncio
import base64
import uuid

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from runefoble_auth.websocket import WS_POLICY_VIOLATION

from tests.helpers.audio_synth import generate_pcm_silence, generate_pcm_sine
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

SPEAKER = "spk-stream-frames-1"


def _granted_session() -> str:
    session_id = str(uuid.uuid4())
    asyncio.run(grant_voice_session(session_id, players=[SPEAKER]))
    return session_id


def _stream_path(session_id: str, query: str) -> str:
    return f"/api/v1/voice/stream/ws/{session_id}/{SPEAKER}?{query}"


def _full_query() -> str:
    return f"campaign_id={uuid.uuid4()}&speaker_name=Valeros"


def _pcm_b64(duration_ms: int = 200) -> str:
    return base64.b64encode(generate_pcm_silence(duration_ms=duration_ms)).decode("ascii")


@pytest.mark.parametrize(
    "bad_frame",
    [
        "{not json",
        '["a", "list"]',
        '{"audio_data": "%%%not-base64%%%"}',
        '{"audio_data": "' + _pcm_b64() + '", "sample_rate": "fast"}',
    ],
)
def test_unparseable_json_frame_gets_invalid_frame_and_the_stream_stays_open(
    client: TestClient, bad_frame: str
):
    """One bad frame gets one INVALID_FRAME error. The next valid frame gets a chunk reply."""
    session_id = _granted_session()

    with client.websocket_connect(
        _stream_path(session_id, _full_query()), subprotocols=voice_ws_subprotocols()
    ) as ws:
        ws.send_text(bad_frame)
        error_frame = ws.receive_json()
        ws.send_json({"audio_data": _pcm_b64()})
        reply = ws.receive_json()

    assert error_frame["type"] == "error"
    assert error_frame["code"] == "INVALID_FRAME"
    assert error_frame["message"]
    assert "error" not in reply
    assert reply["speaker_id"] == SPEAKER
    assert reply["speaker_name"] == "Valeros"
    assert reply["speech_detected"] is False


@pytest.mark.parametrize(
    ("query", "missing"),
    [
        ("speaker_name=Valeros", "campaign_id"),
        (f"campaign_id={uuid.uuid4()}", "speaker_name"),
        ("", "campaign_id"),
    ],
)
def test_missing_query_value_closes_the_socket_with_1008(
    client: TestClient, query: str, missing: str
):
    """A missing campaign id or speaker name is refused. No canned value replaces it."""
    session_id = _granted_session()

    with client.websocket_connect(
        _stream_path(session_id, query), subprotocols=voice_ws_subprotocols()
    ) as ws:
        error_frame = ws.receive_json()
        ws.send_bytes(generate_pcm_sine(duration_ms=100))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()

    assert error_frame["type"] == "error"
    assert error_frame["code"] == "INVALID_REQUEST"
    assert missing in error_frame["message"]
    assert exc.value.code == WS_POLICY_VIOLATION


def test_stream_socket_without_path_ids_is_not_served(client: TestClient):
    """The bare `/ws` route is gone. A socket must name the session and speaker in the path."""
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/api/v1/voice/stream/ws?{_full_query()}", subprotocols=voice_ws_subprotocols()
        ),
    ):
        pass
