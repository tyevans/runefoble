"""Blackbox Frontdoor TDD Tests for Live Tabletop VTT WebSocket Event Mesh & Plugin Slots (TASK-0358).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0005: WebSocket Real-Time Synchronization Architecture
- ADR-0010: Real-time Audio and Tactical Board Synchronization
- ADR-0013: Frontend Microfrontend Architecture
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.dependencies import ws_manager
from gateway_api.main import app as gateway_app

from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client_gw() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def clean_ws_manager():
    """Ensure WebSocket connection manager active connections are clean."""
    ws_manager.active_connections.clear()
    yield
    ws_manager.active_connections.clear()


def test_vtt_websocket_mesh_multi_client_readiness_and_stand_in(client_gw: TestClient) -> None:
    """Verify multi-client WebSocket synchronization for session lobby readiness and stand-in toggles."""
    session_id = f"session-mesh-{uuid4()}"

    with client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols("mesh-tester")
    ) as ws_client_a:
        conn_a = ws_client_a.receive_json()
        assert conn_a["type"] == "connected"
        assert conn_a["session_id"] == session_id

        with client_gw.websocket_connect(
            f"/ws/session/{session_id}", subprotocols=ws_subprotocols("mesh-tester")
        ) as ws_client_b:
            conn_b = ws_client_b.receive_json()
            assert conn_b["type"] == "connected"

            # Client A toggles readiness
            readiness_payload = {
                "type": "player_readiness",
                "userId": "user-valeros",
                "isReady": True,
            }
            ws_client_a.send_json(readiness_payload)

            # Both connected peers receive the readiness broadcast
            msg_b = ws_client_b.receive_json()
            assert msg_b["type"] == "player_readiness"
            assert msg_b["userId"] == "user-valeros"
            assert msg_b["isReady"] is True

            msg_a = ws_client_a.receive_json()
            assert msg_a["type"] == "player_readiness"
            assert msg_a["isReady"] is True

            # Client B toggles AI stand-in for absent player
            stand_in_payload = {
                "type": "player_stand_in",
                "userId": "user-kyra",
                "isAbsent": True,
            }
            ws_client_b.send_json(stand_in_payload)

            msg_a_stand_in = ws_client_a.receive_json()
            assert msg_a_stand_in["type"] == "player_stand_in"
            assert msg_a_stand_in["userId"] == "user-kyra"
            assert msg_a_stand_in["isAbsent"] is True


def test_vtt_websocket_mesh_dice_rolls_and_turn_advancement(client_gw: TestClient) -> None:
    """Verify live dice rolls (updating 3D tray) and turn advancements stream across party members."""
    session_id = f"session-combat-{uuid4()}"

    with client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols("mesh-tester")
    ) as ws_player:
        assert ws_player.receive_json()["type"] == "connected"

        with client_gw.websocket_connect(
            f"/ws/session/{session_id}", subprotocols=ws_subprotocols("mesh-tester")
        ) as ws_dm:
            assert ws_dm.receive_json()["type"] == "connected"

            # Player rolls attack dice
            dice_payload = {
                "type": "dice_rolled",
                "diceType": "d20",
                "formula": "1d20+5",
                "total": 19,
                "targetFaceValue": 14,
                "rollerId": "user-valeros",
                "rollerName": "Valeros",
            }
            ws_player.send_json(dice_payload)

            recv_dm = ws_dm.receive_json()
            assert recv_dm["type"] == "dice_rolled"
            assert recv_dm["diceType"] == "d20"
            assert recv_dm["total"] == 19
            assert recv_dm["targetFaceValue"] == 14

            # DM advances combat initiative turn
            turn_payload = {
                "type": "turn_advanced",
                "activeCombatantId": "token-valeros",
                "roundNumber": 2,
                "turnSecondsRemaining": 60,
            }
            ws_dm.send_json(turn_payload)

            recv_player = ws_player.receive_json()
            # Drain echo of dice roll from player socket first
            if recv_player.get("type") == "dice_rolled":
                recv_player = ws_player.receive_json()

            assert recv_player["type"] == "turn_advanced"
            assert recv_player["activeCombatantId"] == "token-valeros"
            assert recv_player["roundNumber"] == 2


def test_vtt_websocket_mesh_aoe_templates_vfx_and_token_actions(client_gw: TestClient) -> None:
    """Verify AoE spell placements, WebGL particle VFX triggers, and radial menu token actions."""
    session_id = f"session-tactical-{uuid4()}"

    with client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols("mesh-tester")
    ) as ws_caster:
        assert ws_caster.receive_json()["type"] == "connected"

        with client_gw.websocket_connect(
            f"/ws/session/{session_id}", subprotocols=ws_subprotocols("mesh-tester")
        ) as ws_observer:
            assert ws_observer.receive_json()["type"] == "connected"

            # Radial token action (e.g. cast selected from radial menu)
            action_payload = {
                "type": "token_action",
                "action": "cast",
                "tokenId": "token-ezren",
                "tokenName": "Ezren",
            }
            ws_caster.send_json(action_payload)
            recv_action = ws_observer.receive_json()
            assert recv_action["type"] == "token_action"
            assert recv_action["action"] == "cast"
            assert recv_action["tokenId"] == "token-ezren"

            # AoE template placement broadcast
            aoe_payload = {
                "type": "aoe_placed",
                "template": {
                    "shape": "cone",
                    "originX": 3.5,
                    "originY": 4.5,
                    "directionDeg": 45,
                    "radiusFt": 15,
                    "spellName": "Burning Hands",
                },
                "affectedTokenIds": ["token-goblin-1", "token-goblin-2"],
                "affectedCells": [[3, 4], [4, 4], [4, 5]],
            }
            ws_caster.send_json(aoe_payload)
            recv_aoe = ws_observer.receive_json()
            assert recv_aoe["type"] == "aoe_placed"
            assert recv_aoe["template"]["spellName"] == "Burning Hands"
            assert "token-goblin-1" in recv_aoe["affectedTokenIds"]

            # Particle spell VFX trigger broadcast
            vfx_payload = {
                "type": "spell_vfx",
                "vfx": {
                    "spellName": "Fireball",
                    "archetype": "evocation",
                    "origin": {"x": 5, "y": 5},
                    "bloomColor": "#e63946",
                },
            }
            ws_caster.send_json(vfx_payload)
            recv_vfx = ws_observer.receive_json()
            assert recv_vfx["type"] == "spell_vfx"
            assert recv_vfx["vfx"]["spellName"] == "Fireball"

            # DM whisper event
            whisper_payload = {
                "type": "dm_whisper",
                "whisper": {
                    "whisper_id": "whisp-99",
                    "whisper_type": "monster_tactics",
                    "content": "Goblins prepare to retreat behind the barricade.",
                },
            }
            ws_caster.send_json(whisper_payload)
            recv_whisper = ws_observer.receive_json()
            assert recv_whisper["type"] == "dm_whisper"
            assert recv_whisper["whisper"]["whisper_id"] == "whisp-99"
