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

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.companion import mobile_companion_manager
from runefoble_auth.factory import get_spicedb_client
from runefoble_events.voice import (
    MobileAudioProfileAdapted,
    MobileCompanionConnected,
    MobileHapticPingDispatched,
)
from voice_agent.mobile import HapticVibrationPattern, MobileAudioProfileTier

from tests.helpers.ws_identity import ws_subprotocols


@pytest.fixture(autouse=True)
def clean_companion_environment(default_redis_event_bus, mock_bus):
    """Ensure clean SpiceDB, Redis event bus, and companion connection state."""
    mock_spicedb = get_spicedb_client()
    bus = default_redis_event_bus
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()
    yield {"spicedb": mock_spicedb, "redis": mock_bus, "bus": bus}
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()


@pytest.fixture
def client(gateway) -> TestClient:
    return gateway


def _companion_socket(
    client: TestClient, session_id: str, user_id: str, peer_id: str | None = None
):
    """Open a companion socket as a verified `user_id`, optionally naming the peer."""
    path = f"/ws/mobile-companion/{session_id}"
    if peer_id:
        path += f"?peer_id={peer_id}"
    return client.websocket_connect(path, subprotocols=ws_subprotocols(user_id))


def test_zanzibar_unauthorized_connection_rejected(client: TestClient, table_for):
    """A user without `session.observe` is refused with close code 4403."""
    _, session_id = table_for("the_watcher_dm")

    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        _companion_socket(client, session_id, "unauthorized_wanderer") as ws,
    ):
        ws.receive_json()
    assert exc_info.value.code == 4403


def test_authorized_handshake_and_connected_frame(client: TestClient, table_for):
    """Authorized mobile user connects and receives initial 16kHz mono Opus audio profile."""
    user_id = "marcus"
    _, session_id = table_for("the_watcher_dm", {user_id: "player"})

    with _companion_socket(client, session_id, user_id, "peer_marcus") as ws:
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


def test_secret_dm_whisper_haptic_pulse_and_isolation(
    client: TestClient, trusted_ws_issuer, table_for
):
    """Marcus receives secret whisper with triple-pulse haptic vibration; other player is isolated."""
    user_marcus, user_elena, dm_user = "marcus", "elena", "the_watcher_dm"
    _, session_id = table_for(dm_user, {user_marcus: "player", user_elena: "player"})

    with _companion_socket(client, session_id, user_marcus, "peer_marcus") as ws_marcus:
        ws_marcus.receive_json()  # Handshake frame

        with _companion_socket(client, session_id, user_elena, "peer_elena") as ws_elena:
            ws_elena.receive_json()  # Handshake frame

            # DM dispatches secret whisper to Marcus via HTTP frontdoor
            whisper_text = "You feel cold breath upon the back of your neck."
            res = client.post(
                f"/api/v1/mobile/companion/{session_id}/whisper",
                headers={"Authorization": f"Bearer {trusted_ws_issuer.mint(dm_user)}"},
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


def test_combat_turn_initiative_haptic_alert(client: TestClient, trusted_ws_issuer, table_for):
    """Combat turn notification triggers distinct double alert pulse [300, 150, 300]."""
    user_marcus, dm_user = "marcus", "the_watcher_dm"
    _, session_id = table_for(dm_user, {user_marcus: "player"})

    with _companion_socket(client, session_id, user_marcus) as ws:
        ws.receive_json()  # Connected frame

        # Send turn alert via HTTP frontdoor
        res = client.post(
            f"/api/v1/mobile/companion/{session_id}/turn-alert",
            headers={"Authorization": f"Bearer {trusted_ws_issuer.mint(dm_user)}"},
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


def test_adaptive_audio_degradation_over_constrained_cellular(client: TestClient, table_for):
    """Network degradation triggers automatic Opus adaptation from 16kbps to 12kbps and 8kbps."""
    user_id = "marcus"
    _, session_id = table_for("the_watcher_dm", {user_id: "player"})

    with _companion_socket(client, session_id, user_id) as ws:
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
