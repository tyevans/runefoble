"""Blackbox TDD tests for Neural Speech Barge-In and Soft Crossfade Audio Filter (TASK-0168).

Governing ADRs: ADR-0002, ADR-0003, ADR-0007.
Verifies:
  - Speech onset detected in < 40ms via low-latency VAD ring-buffer evaluator.
  - Active TTS playback halted within < 80ms total halt latency.
  - Smooth 20ms cosine crossfade attenuates audio to silence (zero tail pop).
  - Pure silence and sub-threshold noise do not trigger barge-in.
  - NeuralSpeechBargeInDetectedEvent and TTSStreamAttenuatedEvent emitted via Redis Streams.
  - Configurable cosine attenuation duration (10ms-30ms).
  - Strict file length limits (<160 lines per module).
"""

from __future__ import annotations

import array
import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from runefoble_events.voice_barge_in import (
    NeuralSpeechBargeInDetectedEvent,
    TTSStreamAttenuatedEvent,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from voice_agent.main import app, set_event_bus

from tests.helpers.audio_synth import generate_pcm_silence, generate_pcm_sine

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def mock_event_bus(mock_redis: MockAsyncRedis):
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    yield bus
    set_event_bus(None)


@pytest.fixture
def client(mock_event_bus: RedisStreamsEventBus) -> TestClient:
    return TestClient(app)


def test_barge_in_onset_sub_40ms_and_halt_latency_sub_80ms(client: TestClient):
    """Vocalization onset detected in <40ms and audio halted in <80ms total latency."""
    speech_pcm = generate_pcm_sine(duration_ms=100, freq=440.0, amplitude=9000)
    audio_b64 = base64.b64encode(speech_pcm).decode("ascii")

    payload = {
        "session_id": "sess-barge-001",
        "speaker_id": "spk-marcus",
        "speaker_name": "Marcus",
        "audio_base64": audio_b64,
        "fade_duration_ms": 20.0,
        "energy_threshold": 350.0,
    }

    response = client.post("/voice/filters/barge-in/evaluate", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["barge_in_detected"] is True
    assert data["onset_latency_ms"] <= 40.0, f"Onset {data['onset_latency_ms']}ms exceeded 40ms"
    assert data["fade_duration_ms"] == 20.0
    assert data["halt_latency_ms"] < 80.0, f"Halt latency {data['halt_latency_ms']}ms exceeded 80ms"
    assert data["attenuation_applied"] is True
    assert data["attenuated_audio_base64"] is not None


def test_cosine_crossfade_smooth_tail_zero_pop(client: TestClient):
    """Outgoing TTS audio damped to silence with zero tail amplitude and no pop."""
    tts_pcm = generate_pcm_sine(duration_ms=120, freq=300.0, amplitude=16000)
    tts_b64 = base64.b64encode(tts_pcm).decode("ascii")

    human_speech_pcm = generate_pcm_sine(duration_ms=80, freq=440.0, amplitude=8500)
    speech_b64 = base64.b64encode(human_speech_pcm).decode("ascii")

    payload = {
        "session_id": "sess-fade-002",
        "speaker_id": "spk-nadia",
        "speaker_name": "Nadia",
        "audio_base64": speech_b64,
        "outgoing_tts_base64": tts_b64,
        "fade_duration_ms": 20.0,
    }

    response = client.post("/api/v1/voice/filters/barge-in/evaluate", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["attenuation_applied"] is True
    assert data["peak_tail_amplitude"] <= 1, f"Peak tail was {data['peak_tail_amplitude']}"

    faded_bytes = base64.b64decode(data["attenuated_audio_base64"])
    assert len(faded_bytes) == len(tts_pcm)
    samples = array.array("h", faded_bytes)
    assert abs(samples[-1]) <= 1


def test_silence_and_low_noise_suppressed_without_barge_in(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Pure silence or noise below threshold does not trigger interruption or events."""
    silence_pcm = generate_pcm_silence(duration_ms=100)
    payload = {
        "session_id": "sess-quiet-003",
        "speaker_id": "spk-quiet",
        "audio_base64": base64.b64encode(silence_pcm).decode("ascii"),
        "energy_threshold": 350.0,
    }

    res = client.post("/voice/filters/barge-in/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["barge_in_detected"] is False
    assert data["attenuation_applied"] is False
    assert data["halt_latency_ms"] == 0.0

    low_noise_pcm = generate_pcm_sine(duration_ms=100, freq=100.0, amplitude=150)
    payload["audio_base64"] = base64.b64encode(low_noise_pcm).decode("ascii")
    res_noise = client.post("/voice/filters/barge-in/evaluate", json=payload)
    assert res_noise.status_code == 200
    assert res_noise.json()["barge_in_detected"] is False

    assert "runefoble.events.voice" not in mock_redis.streams


def test_cloudevents_dispatched_on_barge_in(client: TestClient, mock_redis: MockAsyncRedis):
    """Dispatches NeuralSpeechBargeInDetectedEvent and TTSStreamAttenuatedEvent to Redis."""
    speech_pcm = generate_pcm_sine(duration_ms=100, freq=500.0, amplitude=9500)
    payload = {
        "session_id": "sess-event-004",
        "speaker_id": "spk-valeros",
        "speaker_name": "Valeros",
        "audio_base64": base64.b64encode(speech_pcm).decode("ascii"),
        "fade_duration_ms": 20.0,
    }

    res = client.post("/voice/filters/barge-in/evaluate", json=payload)
    assert res.status_code == 200

    assert "runefoble.events.voice" in mock_redis.streams
    voice_stream = mock_redis.streams["runefoble.events.voice"]
    assert len(voice_stream) >= 2

    events = [deserialize_event(msg[1]) for msg in voice_stream]
    barge_events = [e for e in events if isinstance(e, NeuralSpeechBargeInDetectedEvent)]
    atten_events = [e for e in events if isinstance(e, TTSStreamAttenuatedEvent)]

    assert len(barge_events) == 1
    assert barge_events[0].session_id == "sess-event-004"
    assert barge_events[0].speaker_id == "spk-valeros"
    assert barge_events[0].onset_latency_ms <= 40.0

    assert len(atten_events) == 1
    assert atten_events[0].session_id == "sess-event-004"
    assert atten_events[0].fade_duration_ms == 20.0
    assert atten_events[0].peak_tail_amplitude <= 1


def test_configurable_fade_duration(client: TestClient):
    """Supports configurable cosine attenuation curve duration (10ms-30ms)."""
    speech_pcm = generate_pcm_sine(duration_ms=100, freq=440.0, amplitude=8000)
    audio_b64 = base64.b64encode(speech_pcm).decode("ascii")

    for fade_ms in (10.0, 15.0, 25.0, 30.0):
        payload = {
            "session_id": f"sess-fade-{int(fade_ms)}",
            "audio_base64": audio_b64,
            "fade_duration_ms": fade_ms,
        }
        res = client.post("/voice/filters/barge-in/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["fade_duration_ms"] == fade_ms
        assert data["halt_latency_ms"] < 80.0


def test_file_length_invariants():
    """Verify Hard Invariant 6: All TASK-0168 modules strictly adhere to line count limits."""
    limits = {
        "services/voice_agent/src/voice_agent/dsp/barge_in_filter.py": 140,
        "services/voice_agent/src/voice_agent/dsp/cosine_crossfade.py": 120,
        "libs/runefoble_events/src/runefoble_events/voice_barge_in.py": 70,
        "services/voice_agent/src/voice_agent/routers/audio_filters.py": 130,
        "tests/test_blackbox_barge_in_filter/test_barge_in_filter.py": 220,
    }
    for rel_path, max_lines in limits.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"{full_path} must exist"
        lines = len(full_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{rel_path} has {lines} lines, exceeding target {max_lines}"
        assert lines < 160 or "test_" in rel_path, (
            f"{rel_path} has {lines} lines, exceeding DoD limit 160"
        )
