"""Frontdoor Blackbox TDD test suite for WebRTC Adaptive Stream Adapter (TASK-0166).

Governing ADRs: ADR-0002, ADR-0003, ADR-0006.
Product Requirements: PRD-0019.
User Stories: US-0059.

Frontdoor Entrypoints:
- HTTP `GET /voice/streams/{session_id}/quality`
- HTTP `POST /voice/streams/{session_id}/report`
- Domain Events: `runefoble.events.voice.stream_quality_degraded`,
                 `runefoble.events.voice.stream_codec_adapted`
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_events.voice_stream_quality import (
    VoiceStreamCodecAdaptedEvent,
    VoiceStreamQualityDegradedEvent,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from voice_agent.main import app, set_event_bus
from voice_agent.routers.stream_diagnostics import reset_diagnostics

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean Redis event bus and stream diagnostics state."""
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    reset_diagnostics()
    yield {"redis": mock_redis, "bus": bus}
    reset_diagnostics()
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_initial_stream_quality_query(client: TestClient):
    """Query baseline stream quality before any RTCP reports."""
    session_id = f"sess-{uuid4().hex[:6]}"
    peer_id = "peer_marcus"

    res = client.get(f"/voice/streams/{session_id}/quality?peer_id={peer_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["peer_id"] == peer_id
    assert data["bitrate_kbps"] == 48
    assert data["sample_rate"] == 16000
    assert data["codec_mode"] == "standard"
    assert data["packet_loss"] == 0.0
    assert data["is_degraded"] is False


def test_packet_loss_steps_down_bitrate_under_200ms(client: TestClient, clean_environment: dict):
    """Simulated packet loss (>5%) steps bitrate down to 12 kbps within 200ms."""
    session_id = f"sess-{uuid4().hex[:6]}"
    peer_id = "peer_mobile_marcus"

    t0 = time.perf_counter()
    report_res = client.post(
        f"/voice/streams/{session_id}/report",
        json={
            "peer_id": peer_id,
            "user_id": "marcus",
            "packet_loss": 0.08,  # 8% packet loss > 5% threshold
            "rtt_ms": 120.0,
            "jitter_ms": 14.5,
        },
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 200.0, f"Bitrate reduction took {elapsed_ms}ms, exceeding 200ms target"

    assert report_res.status_code == 200
    rep_data = report_res.json()
    assert rep_data["adapted"] is True
    assert rep_data["bitrate_kbps"] == 12  # Stepped down to 12 kbps (< 50 kbps)
    assert rep_data["codec_mode"] == "cellular_constrained"
    assert rep_data["is_degraded"] is True
    assert rep_data["fec_enabled"] is True

    # Verify query reflects adapted state
    query_res = client.get(f"/voice/streams/{session_id}/quality?peer_id={peer_id}")
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert q_data["bitrate_kbps"] == 12
    assert q_data["codec_mode"] == "cellular_constrained"
    assert q_data["packet_loss"] == 0.08

    # Verify domain events published to Redis Streams
    mock_redis: MockAsyncRedis = clean_environment["redis"]
    event_types = []
    for _stream, entries in mock_redis.streams.items():
        for _eid, fields in entries:
            event_type = fields.get("event_type") or fields.get("type")
            event_types.append(event_type)
            if event_type == "runefoble.events.voice.stream_codec_adapted":
                payload = json.loads(fields["payload"])
                assert payload["session_id"] == session_id
                assert payload["peer_id"] == peer_id
                assert payload["previous_bitrate_kbps"] == 48
                assert payload["new_bitrate_kbps"] == 12
                assert payload["codec_mode"] == "cellular_constrained"

    assert "runefoble.events.voice.stream_quality_degraded" in event_types
    assert "runefoble.events.voice.stream_codec_adapted" in event_types


def test_severe_loss_and_delay_steps_down_to_ultra_low(client: TestClient):
    """Severe packet loss (18%) steps bitrate down to 8 kbps ultra_low mode."""
    session_id = f"sess-{uuid4().hex[:6]}"
    peer_id = "peer_remote"

    res = client.post(
        f"/voice/streams/{session_id}/report",
        json={
            "peer_id": peer_id,
            "packet_loss": 0.18,  # 18% severe loss
            "rtt_ms": 420.0,
            "jitter_ms": 35.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["adapted"] is True
    assert data["bitrate_kbps"] == 8
    assert data["codec_mode"] == "ultra_low"
    assert data["complexity"] == 3
    assert data["severity"] == "severe"


def test_network_recovery_steps_up_bitrate(client: TestClient):
    """Network stabilization (<2% loss, low RTT) recovers bitrate back to standard."""
    session_id = f"sess-{uuid4().hex[:6]}"
    peer_id = "peer_recovering"

    # Step down first
    client.post(
        f"/voice/streams/{session_id}/report",
        json={"peer_id": peer_id, "packet_loss": 0.10, "rtt_ms": 150.0},
    )

    # Stabilize
    res = client.post(
        f"/voice/streams/{session_id}/report",
        json={"peer_id": peer_id, "packet_loss": 0.01, "rtt_ms": 50.0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["adapted"] is True
    assert data["bitrate_kbps"] == 48
    assert data["codec_mode"] == "standard"
    assert data["reason"] == "network_condition_recovered"


def test_multi_peer_stream_isolation(client: TestClient):
    """Network degradation on mobile participant does not affect other room peers."""
    session_id = f"sess-{uuid4().hex[:6]}"
    peer_mobile, peer_desktop = "peer_mobile", "peer_desktop"

    # Mobile participant experiences packet loss
    client.post(
        f"/voice/streams/{session_id}/report",
        json={"peer_id": peer_mobile, "packet_loss": 0.09, "rtt_ms": 110.0},
    )
    # Desktop participant experiences nominal network
    client.post(
        f"/voice/streams/{session_id}/report",
        json={"peer_id": peer_desktop, "packet_loss": 0.00, "rtt_ms": 25.0},
    )

    res = client.get(f"/voice/streams/{session_id}/quality")
    assert res.status_code == 200
    streams = {s["peer_id"]: s for s in res.json()["streams"]}

    assert streams[peer_mobile]["bitrate_kbps"] == 12
    assert streams[peer_mobile]["codec_mode"] == "cellular_constrained"
    assert streams[peer_desktop]["bitrate_kbps"] == 48
    assert streams[peer_desktop]["codec_mode"] == "standard"


def test_cloudevents_conformance():
    """Verify stream quality domain events conform to CloudEvents 1.0 schema."""
    deg_event = VoiceStreamQualityDegradedEvent(
        session_id="sess-ce",
        peer_id="peer-1",
        packet_loss=0.08,
        round_trip_time_ms=130.0,
        severity="degraded",
    )
    ce_deg = deg_event.to_cloudevent_dict()
    assert ce_deg["specversion"] == "1.0"
    assert ce_deg["type"] == "runefoble.events.voice.stream_quality_degraded"
    assert ce_deg["data"]["packet_loss"] == 0.08

    adapt_event = VoiceStreamCodecAdaptedEvent(
        session_id="sess-ce",
        peer_id="peer-1",
        previous_bitrate_kbps=48,
        new_bitrate_kbps=12,
        codec_mode="cellular_constrained",
    )
    ce_adapt = adapt_event.to_cloudevent_dict()
    assert ce_adapt["specversion"] == "1.0"
    assert ce_adapt["type"] == "runefoble.events.voice.stream_codec_adapted"
    assert ce_adapt["data"]["new_bitrate_kbps"] == 12


def test_file_length_invariants():
    """Verify Hard Invariant 6: All adaptive stream modules strictly under line limits."""
    limits = {
        "services/voice_agent/src/voice_agent/webrtc/quality_monitor.py": 140,
        "services/voice_agent/src/voice_agent/webrtc/adaptive_bitrate.py": 130,
        "services/voice_agent/src/voice_agent/routers/stream_diagnostics.py": 120,
        "libs/runefoble_events/src/runefoble_events/voice_stream_quality.py": 80,
        "tests/test_blackbox_adaptive_stream/test_adaptive_stream.py": 300,
    }
    for rel_path, max_lines in limits.items():
        file_path = REPO_ROOT / rel_path
        assert file_path.is_file(), f"{file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, (
            f"{rel_path} has {lines} lines, exceeding specified limit of {max_lines}"
        )
