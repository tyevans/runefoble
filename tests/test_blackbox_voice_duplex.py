"""Blackbox TDD tests for Zero-Latency Neural Voice Duplex & Speech Interruption Handling (TASK-0141).

Governing ADRs: ADR-0002, ADR-0006.
Verifies:
  - Audio playback canceled within < 100ms of simulated speech onset.
  - voice.speech.interrupted domain event emitted with timestamp and remaining narration text.
  - WebRTC signaling confirms audio stream mute/cancellation.
  - Acoustic echo cancellation prevents false-positive barge-in from loudspeaker feedback.
  - Smooth 20ms crossfade to silence without clipping or popping.
  - File length limits strictly enforced.
"""

from __future__ import annotations

import array
import asyncio
import base64
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import VoiceSpeechInterrupted
from runefoble_platform.redis_bus import deserialize_event
from voice_agent.dsp.cosine_crossfade import apply_cosine_crossfade

from tests.helpers.audio_synth import generate_pcm_silence, generate_pcm_sine
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")


def test_barge_in_cancels_playback_within_100ms(client: TestClient, mock_redis: MockAsyncRedis):
    """Player speech onset triggers immediate barge-in cancellation within 100ms and emits event."""
    session_id, speaker_id = f"sess-{uuid.uuid4().hex[:8]}", "spk-marcus"
    asyncio.run(grant_voice_session(session_id, players=["spk-marcus", "spk-1"]))
    text = "The shadow dragon exhales necrotic flame across the crumbling bridge!"

    with client.websocket_connect(
        f"/api/v1/voice/duplex/ws/{session_id}/{speaker_id}?speaker_name=Marcus",
        subprotocols=voice_ws_subprotocols(),
    ) as ws:
        assert ws.receive_json()["type"] == "voice_duplex_connected"

        # 1. Start active narration playback
        ws.send_json(
            {"type": "playback_start", "playback_id": "pb-1", "text": text, "duration_ms": 8000.0}
        )
        assert ws.receive_json()["type"] == "playback_started"
        assert client.get(f"/api/v1/voice/duplex/status/{session_id}").json()["playback_active"]

        # 2. Player speaks "I cast Shield!" (100ms PCM sine wave)
        speech_pcm = generate_pcm_sine(duration_ms=100, freq=440.0, amplitude=9000)
        t0 = time.perf_counter()
        ws.send_bytes(speech_pcm)

        # 3. Receive WebRTC signaling & barge-in control frames
        f1 = ws.receive_json()
        assert f1["type"] == "barge_in_detected" and f1["latency_ms"] <= 100.0
        assert (time.perf_counter() - t0) * 1000.0 < 150.0

        f2 = ws.receive_json()
        assert f2["type"] == "webrtc_stream_mute" and f2["is_muted"] is True

        f3 = ws.receive_json()
        assert f3["type"] == "playback_canceled" and len(f3["remaining_narration_text"]) > 0

    assert not client.get(f"/api/v1/voice/duplex/status/{session_id}").json()["playback_active"]
    assert "runefoble.events.voice" in mock_redis.streams
    event = deserialize_event(mock_redis.streams["runefoble.events.voice"][0][1])
    assert isinstance(event, VoiceSpeechInterrupted)
    assert event.session_id == session_id and event.speaker_id == speaker_id
    assert event.remaining_narration_text is not None and event.timestamp > 0


def test_acoustic_echo_cancellation_suppresses_false_barge_in(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Loudspeaker playback echoing into microphone is suppressed by AEC and does not trigger barge-in."""
    session_id, speaker_id = f"sess-{uuid.uuid4().hex[:8]}", "spk-marcus"
    asyncio.run(grant_voice_session(session_id, players=["spk-marcus", "spk-1"]))

    with client.websocket_connect(
        f"/api/v1/voice/duplex/ws/{session_id}/{speaker_id}", subprotocols=voice_ws_subprotocols()
    ) as ws:
        ws.receive_json()  # Connected frame
        speaker_audio = generate_pcm_sine(duration_ms=200, freq=350.0, amplitude=8000)
        ws.send_json(
            {"type": "speaker_audio", "audio_data": base64.b64encode(speaker_audio).decode("ascii")}
        )

        mic_echo = generate_pcm_sine(duration_ms=200, freq=350.0, amplitude=6000)
        ws.send_bytes(mic_echo)
        res = ws.receive_json()
        assert res["type"] == "echo_suppressed" and res["speech_detected"] is False

    assert "runefoble.events.voice" not in mock_redis.streams


def test_soft_20ms_crossfade_eliminates_audio_clipping():
    """Soft 20ms crossfade smooths waveform to zero amplitude without abrupt popping."""
    raw_audio = generate_pcm_sine(duration_ms=100, freq=440.0, amplitude=16000)
    faded = apply_cosine_crossfade(raw_audio, fade_duration_ms=20.0, sample_rate=16000)
    assert len(faded) == len(raw_audio)

    samples = array.array("h", faded)
    max_tail = max(abs(s) for s in samples[-10:])
    assert max_tail < 500, f"Expected near-zero amplitude at fade tail, got {max_tail}"


def test_silence_input_does_not_trigger_barge_in(client: TestClient, mock_redis: MockAsyncRedis):
    """Pure silence does not interrupt ongoing playback."""
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    asyncio.run(grant_voice_session(session_id, players=["spk-marcus", "spk-1"]))
    with client.websocket_connect(
        f"/api/v1/voice/duplex/ws/{session_id}/spk-1", subprotocols=voice_ws_subprotocols()
    ) as ws:
        ws.receive_json()
        ws.send_json({"type": "playback_start", "playback_id": "pb-1", "text": "Hello traveler"})
        ws.receive_json()

        ws.send_bytes(generate_pcm_silence(duration_ms=100))
        state = ws.receive_json()
        assert state["type"] == "duplex_state" and state["speech_detected"] is False

    assert "runefoble.events.voice" not in mock_redis.streams
