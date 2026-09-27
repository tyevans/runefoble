"""Blackbox TDD test suite for Spatial Companion Mobile WebRTC Audio & Haptic Ping Gateway (TASK-0128).

Governing ADRs: ADR-0002, ADR-0005, ADR-0013.
Product Requirements: PRD-0004.
User Stories: US-0059.

Frontdoor Entrypoints:
- WebSocket `/ws/mobile-companion/{session_id}`
- HTTP `POST /api/v1/mobile/companion/{session_id}/whisper`
- HTTP `POST /api/v1/mobile/companion/{session_id}/turn-alert`
- HTTP `GET /api/v1/mobile/companion/profiles`
- Domain Events: `runefoble.events.voice.*`
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
import voice_agent.main as va_main
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.companion import mobile_companion_manager
from gateway_api.main import app, set_event_bus
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_events.voice import (
    MobileAudioProfileAdapted,
    MobileCompanionConnected,
    MobileHapticPingDispatched,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from voice_agent.mobile import HapticVibrationPattern, MobileAudioProfileTier

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_companion_environment():
    """Ensure clean SpiceDB, Redis event bus, and companion connection state."""
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    va_main.set_event_bus(bus)
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()
    yield {"spicedb": mock_spicedb, "redis": mock_redis, "bus": bus}
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()
    va_main.set_event_bus(None)
    set_event_bus(None)
    set_spicedb_client(SpiceDBClient())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_zanzibar_unauthorized_connection_rejected(client: TestClient):
    """Zanzibar authorization denies connection when user lacks session permissions."""
    session_id = f"sess-{uuid4().hex[:6]}"
    unauthorized_user = "unauthorized_wanderer"

    with client.websocket_connect(
        f"/ws/mobile-companion/{session_id}?user_id={unauthorized_user}"
    ) as ws:
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"

        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4003


def test_authorized_handshake_and_connected_frame(client: TestClient):
    """Authorized mobile user connects and receives initial 16kHz mono Opus audio profile."""
    spicedb = get_spicedb_client()
    session_id, user_id = f"sess-{uuid4().hex[:6]}", "marcus"
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))

    with client.websocket_connect(
        f"/ws/mobile-companion/{session_id}?user_id={user_id}&peer_id=peer_marcus"
    ) as ws:
        connected_frame = ws.receive_json()
        assert connected_frame["type"] == "mobile_companion_connected"
        assert connected_frame["session_id"] == session_id
        assert connected_frame["user_id"] == user_id
        assert connected_frame["haptic_supported"] is True

        profile = connected_frame["audio_profile"]
        assert profile["sample_rate"] == 16000
        assert profile["channels"] == 1
        assert profile["codec"] == "opus"
        assert profile["bitrate_kbps"] == 16
        assert profile["fec_enabled"] is True

        patterns = connected_frame["vibration_patterns"]
        assert patterns["secret_whisper"] == HapticVibrationPattern.SECRET_WHISPER
        assert patterns["turn_alert"] == HapticVibrationPattern.TURN_ALERT


def test_secret_dm_whisper_haptic_pulse_and_isolation(client: TestClient):
    """Marcus receives secret whisper with triple-pulse haptic vibration; other player is isolated."""
    spicedb = get_spicedb_client()
    session_id = f"sess-{uuid4().hex[:6]}"
    user_marcus, user_elena, dm_user = "marcus", "elena", "the_watcher_dm"

    for u in (user_marcus, user_elena):
        asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", u))
    asyncio.run(
        spicedb.write_relationship("campaign", session_id, "dungeon_master", "user", dm_user)
    )

    with client.websocket_connect(
        f"/ws/mobile-companion/{session_id}?user_id={user_marcus}&peer_id=peer_marcus"
    ) as ws_marcus:
        ws_marcus.receive_json()  # Handshake frame

        with client.websocket_connect(
            f"/ws/mobile-companion/{session_id}?user_id={user_elena}&peer_id=peer_elena"
        ) as ws_elena:
            ws_elena.receive_json()  # Handshake frame

            # DM dispatches secret whisper to Marcus via HTTP frontdoor
            whisper_text = "You feel cold breath upon the back of your neck."
            res = client.post(
                f"/api/v1/mobile/companion/{session_id}/whisper",
                headers={"X-User-Id": dm_user},
                json={
                    "recipient_id": user_marcus,
                    "content": whisper_text,
                    "sender": "The Watcher",
                    "character_name": "Marcus",
                },
            )
            assert res.status_code == 200
            assert res.json()["status"] == "dispatched"

            # Marcus receives haptic ping frame
            haptic_msg = ws_marcus.receive_json()
            assert haptic_msg["type"] == "haptic_ping"
            assert haptic_msg["alert_type"] == "secret_whisper"
            assert haptic_msg["vibration_pattern"] == [200, 100, 200]
            assert haptic_msg["whisper"]["content"] == whisper_text
            assert haptic_msg["whisper"]["is_secret"] is True
            assert haptic_msg["notification"]["diegetic"] is True
            assert haptic_msg["notification"]["urgent"] is True

            # Elena receives ping frame or test check to verify no whisper leakage
            ws_elena.send_json({"type": "ping"})
            pong = ws_elena.receive_json()
            assert pong["type"] == "pong"


def test_combat_turn_initiative_haptic_alert(client: TestClient):
    """Combat turn notification triggers distinct double alert pulse [300, 150, 300]."""
    spicedb = get_spicedb_client()
    session_id, user_marcus, dm_user = f"sess-{uuid4().hex[:6]}", "marcus", "the_watcher_dm"
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_marcus))
    asyncio.run(
        spicedb.write_relationship("campaign", session_id, "dungeon_master", "user", dm_user)
    )

    with client.websocket_connect(f"/ws/mobile-companion/{session_id}?user_id={user_marcus}") as ws:
        ws.receive_json()  # Connected frame

        # Send turn alert via HTTP frontdoor
        res = client.post(
            f"/api/v1/mobile/companion/{session_id}/turn-alert",
            headers={"X-User-Id": dm_user},
            json={
                "recipient_id": user_marcus,
                "character_name": "Marcus the Tactician",
                "round_num": 2,
            },
        )
        assert res.status_code == 200

        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "haptic_ping"
        assert turn_msg["alert_type"] == "turn_alert"
        assert turn_msg["vibration_pattern"] == [300, 150, 300]
        assert "Marcus the Tactician" in turn_msg["notification"]["body"]
        assert turn_msg["notification"]["round"] == 2


def test_adaptive_audio_degradation_over_constrained_cellular(client: TestClient):
    """Network degradation triggers automatic Opus adaptation from 16kbps to 12kbps and 8kbps."""
    spicedb = get_spicedb_client()
    session_id, user_id = f"sess-{uuid4().hex[:6]}", "marcus"
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))

    with client.websocket_connect(f"/ws/mobile-companion/{session_id}?user_id={user_id}") as ws:
        ws.receive_json()  # Connected frame

        # 1. Mild packet loss (8%) / constrained bandwidth (35 kbps) -> CELLULAR_CONSTRAINED (12 kbps)
        ws.send_json(
            {
                "type": "mobile_telemetry",
                "packet_loss": 0.08,
                "bandwidth_kbps": 35.0,
                "latency_ms": 140.0,
            }
        )
        adapted_1 = ws.receive_json()
        assert adapted_1["type"] == "audio_profile_adapted"
        assert adapted_1["current_tier"] == MobileAudioProfileTier.CELLULAR_CONSTRAINED
        assert adapted_1["profile"]["bitrate_kbps"] == 12
        assert adapted_1["profile"]["sample_rate"] == 16000
        assert adapted_1["profile"]["fec_enabled"] is True

        # 2. Severe packet loss (18%) -> ULTRA_LOW (8 kbps)
        ws.send_json(
            {
                "type": "mobile_telemetry",
                "packet_loss": 0.18,
                "bandwidth_kbps": 18.0,
                "latency_ms": 280.0,
            }
        )
        adapted_2 = ws.receive_json()
        assert adapted_2["type"] == "audio_profile_adapted"
        assert adapted_2["current_tier"] == MobileAudioProfileTier.ULTRA_LOW
        assert adapted_2["profile"]["bitrate_kbps"] == 8
        assert adapted_2["reason"] == "severe_packet_loss"

        # Verify connection stays active
        ws.send_json({"type": "audio_frame", "frame_seq": 101, "sample_rate": 16000})
        ack = ws.receive_json()
        assert ack["type"] == "audio_frame_ack" and ack["frame_seq"] == 101


def test_mobile_companion_cloudevents_conformance():
    """Verify companion domain events conform to CloudEvents specification."""
    conn_event = MobileCompanionConnected(
        session_id="sess-ce-1",
        peer_id="peer-1",
        user_id="user-1",
        connected_at="2026-09-26T20:00:00Z",
    )
    ce_conn = conn_event.to_cloudevent_dict()
    assert ce_conn["specversion"] == "1.0"
    assert ce_conn["type"] == "runefoble.events.voice.mobile_connected"

    adapt_event = MobileAudioProfileAdapted(
        session_id="sess-ce-1",
        peer_id="peer-1",
        user_id="user-1",
        previous_tier="mobile_optimized",
        current_tier="cellular_constrained",
        bitrate_kbps=12,
        reason="high_packet_loss",
    )
    assert adapt_event.to_cloudevent_dict()["type"] == "runefoble.events.voice.profile_adapted"

    haptic_event = MobileHapticPingDispatched(
        session_id="sess-ce-1",
        recipient_id="user-1",
        alert_type="secret_whisper",
        vibration_pattern=[200, 100, 200],
        whisper_content="Secret clue",
        dispatched_at="2026-09-26T20:00:00Z",
    )
    ce_haptic = haptic_event.to_cloudevent_dict()
    assert ce_haptic["type"] == "runefoble.events.voice.haptic_ping"
    assert ce_haptic["data"]["vibration_pattern"] == [200, 100, 200]


def test_companion_file_length_invariants():
    """Verify Hard Invariant 6: All companion modules and test suites strictly under 300 lines."""
    files_to_check = [
        "services/voice_agent/src/voice_agent/mobile.py",
        "gateway/api/src/gateway_api/companion/manager.py",
        "gateway/api/src/gateway_api/companion/endpoint.py",
        "gateway/api/src/gateway_api/companion/router.py",
        "gateway/api/src/gateway_api/companion/__init__.py",
        "gateway/api/src/gateway_api/mobile_companion.py",
        "tests/test_blackbox_mobile_companion.py",
    ]
    for rel in files_to_check:
        path = REPO_ROOT / rel
        assert path.is_file(), f"{path} must exist"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < 300, f"{path.name} has {lines} lines, exceeding 300 lines limit"
