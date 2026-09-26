"""Audio waveform synthesis helpers and shared fixtures for streaming Whisper test suites."""

from __future__ import annotations

import math
import struct
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
)
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus
from voice_agent.main import (
    app as voice_app,
)
from voice_agent.main import (
    set_event_bus as voice_set_event_bus,
)
from voice_agent.main import (
    set_watcher_client,
)
from voice_agent.stt import get_streaming_pipeline


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
def shared_event_bus(mock_redis: MockAsyncRedis) -> Generator[RedisStreamsEventBus]:
    bus = RedisStreamsEventBus(client=mock_redis)
    voice_set_event_bus(bus)
    watcher_set_event_bus(bus)
    yield bus
    voice_set_event_bus(None)
    watcher_set_event_bus(None)


@pytest.fixture
def client(shared_event_bus: RedisStreamsEventBus) -> TestClient:
    get_streaming_pipeline().reset_all()
    # Wire the watcher ASGI transport directly for inter-service communication
    watcher_client = AsyncClient(transport=ASGITransport(app=watcher_app), base_url="http://test")
    set_watcher_client(watcher_client)
    return TestClient(voice_app)
