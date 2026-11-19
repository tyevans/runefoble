"""Audio waveform synthesis helpers and shared fixtures for streaming Whisper test suites."""

from __future__ import annotations

import array
import math
import struct
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.service_credential import expected_service_credential
from voice_agent.main import app as voice_app
from voice_agent.speech_settings import VoiceAgentSettings, build_synthesizer, build_transcriber
from voice_agent.stt import (
    StreamingAudioPipeline,
    get_streaming_pipeline,
    set_streaming_pipeline,
)
from voice_agent.synthesis_engine import get_speech_synthesizer, set_speech_synthesizer
from voice_agent.watcher_intent import ServiceClientWatcherIntent, build_watcher_intent_port

from tests.helpers.fixture_synthesizer import FixtureSynthesizer
from tests.helpers.fixture_transcriber import FixtureTranscriber
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.voice_identity import voice_auth_headers


def generate_pcm_sine(
    duration_ms: int = 100,
    freq: float = 440.0,
    sample_rate: int = 16000,
    amplitude: int = 8000,
) -> bytes:
    """Generate 16-bit mono signed PCM sine wave simulating vocal audio."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    samples = [
        int(amplitude * math.sin(2.0 * math.pi * freq * i / sample_rate))
        for i in range(num_samples)
    ]
    return struct.pack(f"<{num_samples}h", *samples)


def generate_synthetic_audio(duration_sec: float = 0.05, sample_rate: int = 16000) -> bytes:
    """Generate a 220 Hz tone with harmonics as PCM test input for DSP filters."""
    n_samples = max(160, int(duration_sec * sample_rate))
    samples = array.array("h")
    omega = 2.0 * math.pi * 220.0 / sample_rate
    fade_len = int(0.01 * sample_rate)
    for i in range(n_samples):
        theta = i * omega
        val = (
            0.50 * math.sin(theta)
            + 0.25 * math.sin(2 * theta)
            + 0.15 * math.sin(3 * theta)
            + 0.10 * math.sin(4 * theta)
        )
        fade = min(1.0, i / max(1, fade_len), (n_samples - 1 - i) / max(1, fade_len))
        samples.append(max(-32767, min(32767, int(val * fade * 20000))))
    return samples.tobytes()


def generate_pcm_silence(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate 16-bit mono signed PCM silence (zero amplitude)."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    return bytes(num_samples * 2)


def generate_wav_sine(
    duration_ms: int = 100,
    freq: float = 440.0,
    sample_rate: int = 16000,
    amplitude: int = 8000,
) -> bytes:
    """Generate a standard 44-byte WAV header containing 16-bit mono PCM."""
    pcm_bytes = generate_pcm_sine(duration_ms, freq, sample_rate, amplitude)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(pcm_bytes)
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size for PCM
        1,  # AudioFormat (PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_bytes


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def speech_engine() -> FixtureTranscriber:
    """The fake STT engine injected at the test composition root. Tests script its transcripts."""
    return FixtureTranscriber()


@pytest.fixture
def fake_speech_synthesizer(seam_restorer: SeamRestorer) -> Generator[FixtureSynthesizer]:
    """Inject the fake TTS engine at the test composition root and restore the default after."""
    fake = FixtureSynthesizer()
    seam_restorer.replace(get_speech_synthesizer, set_speech_synthesizer, fake)
    yield fake


def keep_speech_seams(seam_restorer: SeamRestorer) -> None:
    """Record the STT pipeline and TTS engine, and put them back at teardown.

    Call this before the test sets its environment. The seam getters build lazily from the
    environment, so a value built after the environment changed would leak into later tests.
    """
    seam_restorer.keep(get_streaming_pipeline, set_streaming_pipeline)
    seam_restorer.keep(get_speech_synthesizer, set_speech_synthesizer)


def build_speech_seams_from_env() -> None:
    """Build the STT pipeline and TTS engine from the current environment.

    Call this after the test sets its environment. `keep_speech_seams` restores the values at teardown.
    """
    set_streaming_pipeline(
        StreamingAudioPipeline(
            transcriber=build_transcriber(VoiceAgentSettings()),
            watcher=build_watcher_intent_port(PlatformSettings()),
        )
    )
    set_speech_synthesizer(build_synthesizer(VoiceAgentSettings()))


@pytest.fixture
def shared_event_bus(
    mock_redis: MockAsyncRedis,
    speech_engine: FixtureTranscriber,
    use_redis_client,
    seam_restorer: SeamRestorer,
) -> RedisStreamsEventBus:
    """Route the voice pipeline to the fake transcriber. Teardown restores the previous pipeline."""
    seam_restorer.replace(
        get_streaming_pipeline,
        set_streaming_pipeline,
        StreamingAudioPipeline(
            transcriber=speech_engine, watcher=build_watcher_intent_port(PlatformSettings())
        ),
    )
    return use_redis_client(mock_redis)


@pytest.fixture
def client(shared_event_bus: RedisStreamsEventBus, trusted_voice_issuer) -> TestClient:
    get_streaming_pipeline().reset_all()
    # Route the Watcher port to the in-process Watcher app through the shared service client.
    get_streaming_pipeline().watcher = ServiceClientWatcherIntent(
        "http://test",
        expected_service_credential(),
        transport=ASGITransport(app=watcher_app),
    )
    return TestClient(voice_app, headers=voice_auth_headers())
