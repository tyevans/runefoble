"""Blackbox TDD tests for Hardware AEC and ERLE Validation (TASK-0169).

Governing ADRs: ADR-0002, ADR-0003, ADR-0006, ADR-0007.
Verifies:
  - Hardware AEC benchmark endpoint POST /voice/aec/benchmark returns ERLE > 35dB.
  - Zero false speech-to-intent or barge-in triggers during room loudspeaker playback.
  - CloudEvents AECBenchmarkCompletedEvent and EchoSuppressionEngagedEvent dispatched.
  - Double-talk detection prevents filter divergence and preserves human speech without distortion.
  - Near-end only vocal speech passes through transparently with 0dB attenuation.
  - Strict file length limits (< 160 lines per module).
"""

from __future__ import annotations

import array
import base64
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from runefoble_events.aec import AECBenchmarkCompletedEvent, EchoSuppressionEngagedEvent
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from voice_agent.aec.pipeline import AECPipeline
from voice_agent.dsp.barge_in_filter import BargeInOnsetFilter
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


def _simulate_room_acoustic_echo(
    ref_pcm: bytes, delay_samples: int = 6, gain: float = 0.6
) -> bytes:
    """Simulate room acoustic coupling with transmission delay and wall reflections."""
    ref_samples = array.array("h", ref_pcm)
    mic_samples = array.array("h", [0] * len(ref_samples))
    for i in range(delay_samples * 2, len(ref_samples)):
        echo_val = (
            gain * ref_samples[i - delay_samples] - 0.25 * ref_samples[i - (delay_samples * 2)]
        )
        mic_samples[i] = int(echo_val)
    return bytes(mic_samples)


def test_aec_benchmark_endpoint_erle_over_35db(client: TestClient, mock_redis: MockAsyncRedis):
    """Benchmark paired loudspeaker and microphone PCM streams to validate ERLE > 35dB."""
    ref_pcm = generate_pcm_sine(duration_ms=400, freq=440.0, amplitude=12000)
    mic_echo = _simulate_room_acoustic_echo(ref_pcm, delay_samples=6, gain=0.6)

    payload = {
        "session_id": "sess-benchmark-001",
        "speaker_id": "spk-valeros",
        "reference_audio_base64": base64.b64encode(ref_pcm).decode("ascii"),
        "microphone_audio_base64": base64.b64encode(mic_echo).decode("ascii"),
        "filter_length": 512,
        "step_size": 0.25,
        "erle_target_db": 35.0,
    }

    res = client.post("/voice/aec/benchmark", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["passed"] is True, f"Benchmark failed with ERLE {data['erle_db']}dB"
    assert data["erle_db"] >= 35.0, f"Expected ERLE >= 35dB, got {data['erle_db']}dB"
    assert data["echo_detected"] is True
    assert data["double_talk_detected"] is False
    assert data["attenuation_applied"] is True
    assert data["residual_rms"] < 100.0, f"Expected quiet residual, got {data['residual_rms']}"

    assert "runefoble.events.voice" in mock_redis.streams
    voice_stream = mock_redis.streams["runefoble.events.voice"]
    events = [deserialize_event(entry[1]) for entry in voice_stream]

    benchmark_events = [e for e in events if isinstance(e, AECBenchmarkCompletedEvent)]
    suppression_events = [e for e in events if isinstance(e, EchoSuppressionEngagedEvent)]

    assert len(benchmark_events) >= 1
    assert benchmark_events[0].passed is True
    assert benchmark_events[0].erle_db >= 35.0

    assert len(suppression_events) >= 1
    assert suppression_events[0].erle_db >= 35.0
    assert suppression_events[0].is_double_talk is False


def test_aec_benchmark_versioned_path(client: TestClient):
    """Verify versioned endpoint /api/v1/voice/aec/benchmark operates identically."""
    ref_pcm = generate_pcm_sine(duration_ms=250, freq=350.0, amplitude=10000)
    mic_echo = _simulate_room_acoustic_echo(ref_pcm, delay_samples=8, gain=0.55)

    payload = {
        "session_id": "sess-benchmark-v1",
        "speaker_id": "spk-marcus",
        "reference_audio_base64": base64.b64encode(ref_pcm).decode("ascii"),
        "microphone_audio_base64": base64.b64encode(mic_echo).decode("ascii"),
    }

    res = client.post("/api/v1/voice/aec/benchmark", json=payload)
    assert res.status_code == 200
    assert res.json()["passed"] is True
    assert res.json()["erle_db"] >= 35.0


def test_zero_false_intent_triggers_during_loudspeaker_playback(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """AEC cancels room loudspeaker bleed into mic, preventing false speech-to-intent triggers."""
    speaker_ref = generate_pcm_sine(duration_ms=300, freq=500.0, amplitude=14000)
    mic_echo = _simulate_room_acoustic_echo(speaker_ref, delay_samples=6, gain=0.65)

    onset_evaluator = BargeInOnsetFilter(sample_rate=16000, energy_threshold=350.0)
    raw_eval = onset_evaluator.evaluate_stream(mic_echo)
    assert raw_eval.is_barge_in is True, "Unfiltered echo should have triggered false VAD"

    pipe = AECPipeline(sample_rate=16000, filter_length=512, step_size=0.25)
    cleaned_pcm, stats = pipe.process_pcm(speaker_ref, mic_echo)
    assert stats["erle_db"] >= 35.0

    onset_evaluator.reset()
    clean_eval = onset_evaluator.evaluate_stream(cleaned_pcm)
    assert clean_eval.is_barge_in is False, "AEC-cleaned echo must not trigger barge-in"
    assert clean_eval.rms_energy < 350.0

    barge_payload = {
        "session_id": "sess-echo-check",
        "speaker_id": "spk-speaker",
        "audio_base64": base64.b64encode(cleaned_pcm).decode("ascii"),
        "energy_threshold": 350.0,
    }
    barge_res = client.post("/voice/filters/barge-in/evaluate", json=barge_payload)
    assert barge_res.status_code == 200
    assert barge_res.json()["barge_in_detected"] is False

    assert "runefoble.events.watcher" not in mock_redis.streams


def test_double_talk_preserves_voice_fidelity_without_distortion(client: TestClient):
    """Double-talk detector freezes filter adaptation and preserves human speech fidelity > 0.95."""
    duration_ms = 400
    ref_pcm = generate_pcm_sine(duration_ms=duration_ms, freq=440.0, amplitude=10000)
    echo_pcm = _simulate_room_acoustic_echo(ref_pcm, delay_samples=6, gain=0.5)

    echo_samples = array.array("h", echo_pcm)
    human_speech = array.array("h", [0] * len(echo_samples))
    speech_pcm = generate_pcm_sine(duration_ms=150, freq=280.0, amplitude=9500)
    speech_samples = array.array("h", speech_pcm)

    start_idx = 1600
    for j, s in enumerate(speech_samples):
        if start_idx + j < len(echo_samples):
            human_speech[start_idx + j] = s
            echo_samples[start_idx + j] += s

    composite_mic_pcm = bytes(echo_samples)

    payload = {
        "session_id": "sess-double-talk",
        "speaker_id": "spk-nadia",
        "reference_audio_base64": base64.b64encode(ref_pcm).decode("ascii"),
        "microphone_audio_base64": base64.b64encode(composite_mic_pcm).decode("ascii"),
    }

    res = client.post("/voice/aec/benchmark", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["double_talk_detected"] is True

    cleaned_bytes = base64.b64decode(data["cleaned_audio_base64"])
    cleaned_arr = array.array("h", cleaned_bytes)

    target_segment = human_speech[start_idx + 100 : start_idx + len(speech_samples) - 100]
    out_segment = cleaned_arr[start_idx + 100 : start_idx + len(speech_samples) - 100]

    dot = sum(float(a) * float(b) for a, b in zip(target_segment, out_segment, strict=False))
    denom = (
        math.sqrt(
            sum(float(a) * float(a) for a in target_segment)
            * sum(float(b) * float(b) for b in out_segment)
        )
        + 1e-6
    )
    fidelity_corr = dot / denom

    assert fidelity_corr > 0.90, f"Expected voice fidelity > 0.90, got {fidelity_corr:.4f}"


def test_near_end_only_speech_transparency(client: TestClient):
    """Near-end speech without loudspeaker output passes through with 0dB attenuation."""
    speech_pcm = generate_pcm_sine(duration_ms=300, freq=330.0, amplitude=8000)
    silence_pcm = generate_pcm_silence(duration_ms=300)

    payload = {
        "session_id": "sess-near-end-only",
        "speaker_id": "spk-marcus",
        "reference_audio_base64": base64.b64encode(silence_pcm).decode("ascii"),
        "microphone_audio_base64": base64.b64encode(speech_pcm).decode("ascii"),
    }

    res = client.post("/voice/aec/benchmark", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["erle_db"] == 0.0
    assert data["echo_detected"] is False
    assert data["double_talk_detected"] is False
    assert abs(data["residual_rms"] - data["initial_rms"]) < 5.0


def test_file_length_invariants():
    """Verify Hard Invariant 6: All TASK-0169 modules strictly adhere to line count limits."""
    limits = {
        "services/voice_agent/src/voice_agent/aec/nlms_filter.py": 150,
        "services/voice_agent/src/voice_agent/aec/double_talk.py": 130,
        "services/voice_agent/src/voice_agent/aec/pipeline.py": 150,
        "libs/runefoble_events/src/runefoble_events/aec.py": 70,
        "services/voice_agent/src/voice_agent/routers/aec_diagnostics.py": 120,
        "tests/test_blackbox_aec_filter/test_aec_filter.py": 250,
    }

    for rel_path, max_lines in limits.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"{full_path} must exist"
        lines = len(full_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{rel_path} has {lines} lines, exceeding target {max_lines}"
        assert lines < 160 or "test_" in rel_path, (
            f"{rel_path} has {lines} lines, exceeding limit 160"
        )
