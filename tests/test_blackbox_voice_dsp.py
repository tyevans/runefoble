"""Blackbox TDD tests for Voice Agent Dynamic DSP Audio Conditioning Pipeline.

Interacts strictly through public HTTP frontdoors (POST /api/v1/voice/dsp/apply,
POST /api/v1/voice/tts) and validates observable responses, DSP frequency modulation
metadata, audio payloads, processing latency (<50ms), and emitted domain events.
"""

import asyncio
import base64
import json
import time

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import VoiceAudioConditioned
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.main import app, set_event_bus

from tests.helpers.audio_synth import generate_pcm_sine
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers


@pytest.fixture(autouse=True)
def _voice_session_grants() -> None:
    """Make the DM and the speakers of these literal sessions authorized through the SpiceDB seam."""
    for session_id in (
        "session_default",
        "sess-bench-1",
        "sess-drunk-1",
        "sess-ethereal-1",
        "session-conditioned-99",
        "sess-tts-combo-1",
        "sess-underwater-1",
        "sess-whisper-1",
    ):
        asyncio.run(
            grant_voice_session(
                session_id,
                players=[
                    "speaker_default",
                    "speaker-sarah-42",
                    "spk-bench",
                    "spk-kyra",
                    "spk-marcus",
                    "spk-sarah",
                    "spk-valeros",
                    "spk-watcher",
                ],
            )
        )


pytestmark = pytest.mark.usefixtures("trusted_voice_issuer", "fake_speech_synthesizer")

# DSP filters only transform supplied audio, so every apply request carries input PCM.
INPUT_AUDIO_B64 = base64.b64encode(generate_pcm_sine(duration_ms=100)).decode("ascii")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=voice_auth_headers())


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture(autouse=True)
def mock_event_bus(mock_redis: MockAsyncRedis):
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    yield bus
    set_event_bus(None)


# ---------------------------------------------------------------------------
# 1. Frontdoor DSP Filter Presets via POST /api/v1/voice/dsp/apply
# ---------------------------------------------------------------------------


def test_dsp_apply_whisper_filter(client: TestClient):
    """POST /api/v1/voice/dsp/apply with filter='whisper' produces reduced dynamic range and high-pass shimmer."""
    payload = {
        "audio_base64": INPUT_AUDIO_B64,
        "filter": "whisper",
        "session_id": "sess-whisper-1",
        "speaker_id": "spk-sarah",
        "speaker_name": "Sarah Stand-in",
    }
    response = client.post("/api/v1/voice/dsp/apply", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify audio payload
    assert "audio_payload" in data
    assert len(data["audio_payload"]) > 0
    audio_bytes = base64.b64decode(data["audio_payload"])
    assert len(audio_bytes) > 0
    assert data["audio_bytes_length"] == len(audio_bytes)

    # Verify filter metadata
    assert "whisper" in data["filters_applied"]
    metadata = data["dsp_metadata"]
    assert metadata.get("reduced_dynamic_range") is True
    assert metadata.get("high_pass_shimmer") is True
    assert "dynamic_range_ratio" in metadata
    assert "high_pass_cutoff_hz" in metadata
    assert data["latency_ms"] < 100.0


def test_dsp_apply_underwater_filter(client: TestClient):
    """POST /api/v1/voice/dsp/apply with filter='underwater' produces muffled low-pass and sub-bass resonance."""
    payload = {
        "audio_base64": INPUT_AUDIO_B64,
        "filter": "underwater",
        "session_id": "sess-underwater-1",
        "speaker_id": "spk-marcus",
        "speaker_name": "Marcus Adventurer",
    }
    response = client.post("/api/v1/voice/dsp/apply", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify audio payload
    assert len(data["audio_payload"]) > 0
    audio_bytes = base64.b64decode(data["audio_payload"])
    assert len(audio_bytes) > 0

    # Verify filter metadata
    assert "underwater" in data["filters_applied"]
    metadata = data["dsp_metadata"]
    assert metadata.get("muffled_low_pass") is True
    assert metadata.get("sub_bass_resonance") is True
    assert "low_pass_cutoff_hz" in metadata
    assert "sub_bass_boost_db" in metadata
    assert data["latency_ms"] < 100.0


def test_dsp_apply_ethereal_filter(client: TestClient):
    """POST /api/v1/voice/dsp/apply with filter='ethereal' produces ghostly echo modulation and delay tail."""
    payload = {
        "audio_base64": INPUT_AUDIO_B64,
        "filter": "ethereal",
        "session_id": "sess-ethereal-1",
        "speaker_id": "spk-watcher",
        "speaker_name": "The Watcher",
    }
    response = client.post("/api/v1/voice/dsp/apply", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify audio payload
    assert len(data["audio_payload"]) > 0
    audio_bytes = base64.b64decode(data["audio_payload"])
    assert len(audio_bytes) > 0

    # Verify filter metadata
    assert "ethereal" in data["filters_applied"]
    metadata = data["dsp_metadata"]
    assert metadata.get("ghostly_echo_modulation") is True
    assert metadata.get("delay_tail") is True
    assert "echo_delay_ms" in metadata or "delay_ms" in metadata
    assert data["latency_ms"] < 100.0


def test_dsp_apply_drunk_filter(client: TestClient):
    """POST /api/v1/voice/dsp/apply with filter='drunk' produces slurred formant modulation and pitch sway."""
    payload = {
        "audio_base64": INPUT_AUDIO_B64,
        "filter": "drunk",
        "session_id": "sess-drunk-1",
        "speaker_id": "spk-valeros",
        "speaker_name": "Valeros Fighter",
    }
    response = client.post("/api/v1/voice/dsp/apply", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify audio payload
    assert len(data["audio_payload"]) > 0
    audio_bytes = base64.b64decode(data["audio_payload"])
    assert len(audio_bytes) > 0

    # Verify filter metadata
    assert "drunk" in data["filters_applied"]
    metadata = data["dsp_metadata"]
    assert metadata.get("slurred_formant_modulation") is True
    assert metadata.get("pitch_sway") is True
    assert "pitch_sway_cents" in metadata
    assert data["latency_ms"] < 100.0


# ---------------------------------------------------------------------------
# 2. TTS Integration with Multiple Filters
# ---------------------------------------------------------------------------


def test_tts_multiple_filters_audio_payload_and_metadata(client: TestClient):
    """POST /api/v1/voice/tts accepting filters=['drunk', 'ethereal'] returns audio payload and DSP metadata."""
    payload = {
        "text": "By the gods of the sun, we shall breach this dungeon gate!",
        "persona_id": "kyra_stand_in",
        "filters": ["drunk", "ethereal"],
        "session_id": "sess-tts-combo-1",
        "speaker_id": "spk-kyra",
        "speaker_name": "Kyra Stand-in",
    }
    response = client.post("/api/v1/voice/tts", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Check audio payload and DSP metadata presence
    assert "audio_payload" in data
    assert len(data["audio_payload"]) > 0
    audio_bytes = base64.b64decode(data["audio_payload"])
    assert len(audio_bytes) > 0

    assert "dsp_metadata" in data
    metadata = data["dsp_metadata"]
    assert metadata.get("pitch_sway") is True or metadata.get("slurred_formant_modulation") is True
    assert metadata.get("delay_tail") is True or metadata.get("ghostly_echo_modulation") is True

    # Effects and text transforms
    assert "drunk" in data["effects_applied"]
    assert "ethereal" in data["effects_applied"]
    assert "*hic!*" in data["conditioned_text"]


# ---------------------------------------------------------------------------
# 3. Benchmark DSP Latency Under 50ms
# ---------------------------------------------------------------------------


def test_benchmark_dsp_latency_sub_50ms(client: TestClient, mock_event_bus):
    """Benchmark latency: verify DSP filter processing runs strictly under 50ms."""
    payload = {
        "audio_base64": INPUT_AUDIO_B64,
        "filters": ["drunk", "underwater", "ethereal"],
        "session_id": "sess-bench-1",
        "speaker_id": "spk-bench",
        "speaker_name": "Benchmark Tester",
    }

    # Warmup
    warmup_res = client.post("/api/v1/voice/dsp/apply", json=payload)
    assert warmup_res.status_code == 200

    latencies = []
    for _ in range(25):
        t0 = time.perf_counter()
        res = client.post("/api/v1/voice/dsp/apply", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert res.status_code == 200
        latencies.append(elapsed_ms)
        data = res.json()
        assert data["latency_ms"] < 100.0

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    assert avg_latency < 50.0, f"Average latency {avg_latency:.2f}ms exceeded 50ms limit"
    assert max_latency < 100.0, f"Peak latency {max_latency:.2f}ms exceeded 100ms limit"


# ---------------------------------------------------------------------------
# 4. Domain Event Dispatch Verification
# ---------------------------------------------------------------------------


def test_dsp_apply_dispatches_voice_audio_conditioned_event(
    client: TestClient, mock_event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
):
    """Verify event dispatch of VoiceAudioConditioned upon DSP conditioning."""
    payload = {
        "audio_base64": INPUT_AUDIO_B64,
        "filters": ["whisper", "ethereal"],
        "session_id": "session-conditioned-99",
        "speaker_id": "speaker-sarah-42",
        "speaker_name": "Sarah",
    }
    response = client.post("/api/v1/voice/dsp/apply", json=payload)
    assert response.status_code == 200, response.text

    # Verify event published in Redis stream
    streams = mock_redis.streams
    found_event = False
    for _stream_name, entries in streams.items():
        for _entry_id, fields in entries:
            event_type = fields.get("event_type") or fields.get("type")
            if event_type == "runefoble.events.voice.audio_conditioned":
                found_event = True
                payload_data = json.loads(fields["payload"])
                assert payload_data["session_id"] == "session-conditioned-99"
                assert payload_data["speaker_id"] == "speaker-sarah-42"
                assert payload_data["speaker_name"] == "Sarah"
                assert "whisper" in payload_data["filters_applied"]
                assert "ethereal" in payload_data["filters_applied"]
                assert float(payload_data["latency_ms"]) < 100.0
                assert int(payload_data["audio_bytes_length"]) > 0
                # Verify schema conformity via VoiceAudioConditioned
                event_model = VoiceAudioConditioned.model_validate(payload_data)
                assert event_model.session_id == "session-conditioned-99"

    assert found_event, (
        f"VoiceAudioConditioned event not found in Redis streams: {list(streams.keys())}"
    )
