"""Blackbox tests for malformed WAV input on the voice frontdoors (TASK-0850).

A RIFF body that cannot be parsed is rejected. It is never read as raw PCM. The HTTP routes
return 400 with the stable error code `audio_format_invalid`. The audio WebSocket sends a typed
error frame and keeps the stream open. No player speech is recorded in either case.
"""

from __future__ import annotations

import asyncio
import base64
import struct
import uuid

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import PlayerSpokeEvent
from runefoble_platform.event_deserializer import deserialize_event

from tests.helpers.audio_synth import generate_pcm_silence, generate_pcm_sine, generate_wav_sine
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

TRANSCRIBE_URL = "/api/v1/voice/transcribe"
CHUNK_URL = "/api/v1/voice/stream/chunk"
SESSION_STREAM = "runefoble.events.session"
WATCHER_STREAM = "runefoble.events.watcher"
ERROR_CODE = "audio_format_invalid"
SPEAKER = "spk-malformed-wav-1"


def _riff_without_data_chunk() -> bytes:
    """A RIFF/WAVE body of 52 bytes: a fmt chunk and a LIST chunk, and no data chunk."""
    fmt_payload = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
    fmt_chunk = b"fmt " + struct.pack("<I", len(fmt_payload)) + fmt_payload
    list_chunk = b"LIST" + struct.pack("<I", 8) + b"INFOabcd"
    body = b"WAVE" + fmt_chunk + list_chunk
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _short_riff_header() -> bytes:
    """A RIFF body shorter than the 44-byte canonical header."""
    return b"RIFF" + struct.pack("<I", 20) + b"WAVEfmt " + b"\x00" * 4


def _granted_session(speaker_id: str = SPEAKER) -> str:
    session_id = str(uuid.uuid4())
    asyncio.run(grant_voice_session(session_id, players=[speaker_id]))
    return session_id


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _player_spoke_events(mock_redis: MockAsyncRedis) -> list[PlayerSpokeEvent]:
    return [
        deserialize_event(fields)
        for _id, fields in mock_redis.streams.get(SESSION_STREAM, [])
        if isinstance(deserialize_event(fields), PlayerSpokeEvent)
    ]


@pytest.mark.parametrize("malformed", [_riff_without_data_chunk(), _short_riff_header()])
def test_transcribe_rejects_malformed_riff_with_stable_code(
    client: TestClient, mock_redis: MockAsyncRedis, malformed: bytes
):
    """A malformed RIFF body returns 400 and the stable code. No speech is recorded."""
    session_id = _granted_session()
    resp = client.post(
        TRANSCRIBE_URL,
        json={
            "speaker_id": SPEAKER,
            "speaker_name": "Valeros",
            "session_id": session_id,
            "campaign_id": str(uuid.uuid4()),
            "audio_base64": _b64(malformed),
        },
    )

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == ERROR_CODE
    assert _player_spoke_events(mock_redis) == []
    assert WATCHER_STREAM not in mock_redis.streams


def test_transcribe_accepts_valid_wav_with_the_same_transcript(
    client: TestClient, mock_redis: MockAsyncRedis, speech_engine
):
    """A valid WAV container is decoded. The engine text becomes the player action."""
    speech_engine.script("cast magic missile")
    session_id = _granted_session()
    resp = client.post(
        TRANSCRIBE_URL,
        json={
            "speaker_id": SPEAKER,
            "speaker_name": "Valeros",
            "session_id": session_id,
            "campaign_id": str(uuid.uuid4()),
            "audio_base64": _b64(generate_wav_sine(duration_ms=300)),
        },
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["transcript"] == "cast magic missile"
    assert [e.transcript for e in _player_spoke_events(mock_redis)] == ["cast magic missile"]


def test_stream_chunk_rejects_malformed_riff_with_stable_code(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """The HTTP chunk route returns 400 for a RIFF body with no data chunk. Nothing is recorded."""
    session_id = _granted_session()
    resp = client.post(
        CHUNK_URL,
        json={
            "session_id": session_id,
            "speaker_id": SPEAKER,
            "speaker_name": "Valeros",
            "audio_data": _b64(_riff_without_data_chunk()),
            "is_final": True,
        },
    )

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == ERROR_CODE
    assert _player_spoke_events(mock_redis) == []


def test_audio_websocket_sends_typed_error_frame_and_keeps_stream_open(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """A malformed binary frame gets a typed error frame. A valid frame after it still works."""
    session_id = _granted_session()
    path = f"/api/v1/voice/stream/ws/{session_id}/{SPEAKER}"

    with client.websocket_connect(path, subprotocols=voice_ws_subprotocols()) as ws:
        ws.send_bytes(_riff_without_data_chunk())
        error_frame = ws.receive_json()
        ws.send_bytes(generate_pcm_silence(duration_ms=200))
        next_frame = ws.receive_json()

    assert error_frame["error"] == ERROR_CODE
    assert "transcript" not in error_frame
    assert next_frame["speech_detected"] is False
    assert next_frame["transcript"] is None
    assert _player_spoke_events(mock_redis) == []


def test_audio_websocket_valid_pcm_still_processed(client: TestClient):
    """Valid PCM on the socket still returns a normal chunk result."""
    session_id = _granted_session()
    path = f"/api/v1/voice/stream/ws/{session_id}/{SPEAKER}"

    with client.websocket_connect(path, subprotocols=voice_ws_subprotocols()) as ws:
        ws.send_bytes(generate_pcm_sine(duration_ms=100))
        frame = ws.receive_json()

    assert "error" not in frame
    assert frame["speaker_id"] == SPEAKER
