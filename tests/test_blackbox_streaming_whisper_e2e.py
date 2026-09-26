"""Blackbox TDD tests for End-to-End Streaming Speech-to-Intent Pipeline (TASK-0039).

Verifies sub-500ms latency budget, continuous WebSocket frontdoor audio streaming,
immediate forced utterance completion via is_final, and multi-speaker ring buffer isolation.
"""

from __future__ import annotations

import base64
import time
import uuid

from fastapi.testclient import TestClient
from runefoble_events.events import (
    PlayerSpokeEvent,
    SpeechIntentParsed,
)
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    deserialize_event,
)

from tests.helpers.audio_synth import (
    generate_pcm_silence,
    generate_pcm_sine,
)


def test_end_to_end_streaming_speech_to_intent_latency_budget(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Verifies end-to-end streaming speech transcription and Watcher intent parsing strictly within 500ms."""
    session_id = str(uuid.uuid4())
    campaign_id = str(uuid.uuid4())

    speech_pcm = generate_pcm_sine(duration_ms=300)
    silence_pcm = generate_pcm_silence(duration_ms=200)

    # 1. Send speech
    client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-valeros-1",
            "speaker_name": "Valeros",
            "campaign_id": campaign_id,
            "audio_data": base64.b64encode(speech_pcm).decode("ascii"),
            "mock_transcript": "advance 2 east",
        },
    )

    # 2. Send silence to trigger completion and measure roundtrip
    t0 = time.perf_counter()
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-valeros-1",
            "speaker_name": "Valeros",
            "campaign_id": campaign_id,
            "audio_data": base64.b64encode(silence_pcm).decode("ascii"),
            "mock_transcript": "advance 2 east",
        },
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["utterance_complete"] is True
    assert data["transcript"] == "advance 2 east"
    assert data["watcher_intent"] is not None
    assert data["watcher_intent"]["action_type"] == "move"
    assert data["latency_ms"] < 250.0
    assert elapsed_ms < 500.0, f"Roundtrip {elapsed_ms:.2f}ms exceeded 500ms budget"

    # 3. Assert PlayerSpokeEvent in runefoble.events.session
    assert "runefoble.events.session" in mock_redis.streams

    # 4. Assert SpeechIntentParsed in runefoble.events.watcher
    assert "runefoble.events.watcher" in mock_redis.streams
    watcher_entries = mock_redis.streams["runefoble.events.watcher"]
    intent_events = [
        deserialize_event(f)
        for _, f in watcher_entries
        if isinstance(deserialize_event(f), SpeechIntentParsed)
    ]
    assert len(intent_events) >= 1
    intent_event = intent_events[0]
    assert intent_event.speaker_name == "Valeros"
    assert intent_event.action_type == "move"
    assert intent_event.raw_transcript == "advance 2 east"


def test_continuous_stream_over_websocket_frontdoor(client: TestClient, mock_redis: MockAsyncRedis):
    """Continuous PCM audio frame streaming via WebSocket frontdoor dispatches events upon utterance completion."""
    session_id = str(uuid.uuid4())
    speaker_id = "spk-ws-valeros"

    with client.websocket_connect(
        f"/api/v1/voice/stream/ws/{session_id}/{speaker_id}?speaker_name=Valeros"
    ) as ws:
        # Frame 1: 200ms speech
        speech_pcm = generate_pcm_sine(duration_ms=200)
        ws.send_bytes(speech_pcm)
        res1 = ws.receive_json()
        assert res1["speech_detected"] is True
        assert res1["utterance_complete"] is False

        # Frame 2: 200ms silence (< 250ms threshold)
        silence_pcm = generate_pcm_silence(duration_ms=200)
        ws.send_bytes(silence_pcm)
        res2 = ws.receive_json()
        assert res2["utterance_complete"] is True
        assert res2["transcript"] is not None
        assert res2["latency_ms"] < 250.0

    # Verify event bus received PlayerSpokeEvent
    assert "runefoble.events.session" in mock_redis.streams
    _id, fields = mock_redis.streams["runefoble.events.session"][0]
    event = deserialize_event(fields)
    assert isinstance(event, PlayerSpokeEvent)
    assert event.speaker_id == speaker_id
    assert event.speaker_name == "Valeros"


def test_forced_completion_via_is_final(client: TestClient, mock_redis: MockAsyncRedis):
    """Passing is_final=True immediately flushes and transcribes active speech without trailing silence."""
    speech_pcm = generate_pcm_sine(duration_ms=200)
    speech_b64 = base64.b64encode(speech_pcm).decode("ascii")

    session_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-final-1",
            "speaker_name": "Merisiel",
            "audio_data": speech_b64,
            "is_final": True,
            "mock_transcript": "I cast shield",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["utterance_complete"] is True
    assert data["transcript"] == "I cast shield"

    assert "runefoble.events.session" in mock_redis.streams


def test_multi_speaker_buffer_isolation(client: TestClient, mock_redis: MockAsyncRedis):
    """Multiple participants streaming audio concurrently maintain isolated ring buffers and VAD states."""
    session_id = str(uuid.uuid4())

    speech_pcm = generate_pcm_sine(duration_ms=200)
    silence_pcm = generate_pcm_silence(duration_ms=200)

    # Kyra speaks
    client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-kyra",
            "speaker_name": "Kyra",
            "audio_data": base64.b64encode(speech_pcm).decode("ascii"),
            "mock_transcript": "heal Valeros",
        },
    )

    # Valeros is silent
    res_valeros = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-valeros",
            "speaker_name": "Valeros",
            "audio_data": base64.b64encode(silence_pcm).decode("ascii"),
        },
    )
    assert res_valeros.json()["speech_detected"] is False
    assert res_valeros.json()["utterance_complete"] is False

    # Kyra completes utterance via trailing silence
    res_kyra = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-kyra",
            "speaker_name": "Kyra",
            "audio_data": base64.b64encode(silence_pcm).decode("ascii"),
            "mock_transcript": "heal Valeros",
        },
    )
    assert res_kyra.json()["utterance_complete"] is True
    assert res_kyra.json()["transcript"] == "heal Valeros"

    # Only Kyra's event was emitted
    assert len(mock_redis.streams["runefoble.events.session"]) == 1
    event = deserialize_event(mock_redis.streams["runefoble.events.session"][0][1])
    assert event.speaker_id == "spk-kyra"
