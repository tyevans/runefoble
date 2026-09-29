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

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.dependencies import ws_manager
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent


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

    with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws_client_a:
        conn_a = ws_client_a.receive_json()
        assert conn_a["type"] == "connected"
        assert conn_a["session_id"] == session_id

        with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws_client_b:
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

    with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws_player:
        assert ws_player.receive_json()["type"] == "connected"

        with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws_dm:
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

    with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws_caster:
        assert ws_caster.receive_json()["type"] == "connected"

        with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws_observer:
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


def test_vtt_frontend_app_shell_and_plugin_registry_invariants() -> None:
    """Verify App Shell and plugin registry adhere to Hard Invariant 6 and contain all required bindings."""
    app_shell_path = REPO_ROOT / "frontend" / "src" / "runefoble-app.ts"
    registry_path = REPO_ROOT / "frontend" / "src" / "components" / "plugins" / "plugin_registry.ts"

    assert app_shell_path.is_file()
    assert registry_path.is_file()

    app_lines = len(app_shell_path.read_text(encoding="utf-8").splitlines())
    reg_lines = len(registry_path.read_text(encoding="utf-8").splitlines())

    # Hard Invariant 6: File length limit (< 500 lines)
    assert app_lines < 450, f"runefoble-app.ts must be < 450 lines (got {app_lines})"
    assert reg_lines <= 120, f"plugin_registry.ts must be <= 120 lines (got {reg_lines})"

    app_content = app_shell_path.read_text(encoding="utf-8")
    reg_content = registry_path.read_text(encoding="utf-8")

    # Plugin slots registration
    assert "registerDefaultPlugins" in reg_content
    assert "runefoble-initiative-tracker" in reg_content
    assert "runefoble-soundscape-controls" in reg_content
    assert "runefoble-dice-roller" in reg_content
    assert "runefoble-dice-tray-3d" in reg_content
    assert "runefoble-combat-reaction-prompt" in reg_content
    assert "runefoble-dm-whisper-bar" in reg_content
    assert "runefoble-dm-trap-controls" in reg_content

    # App shell lobby event integration
    assert "@toggle-readiness=" in app_content
    assert "@toggle-stand-in=" in app_content
    assert "'player_readiness'" in app_content
    assert "'player_stand_in'" in app_content

    # App shell board integration & dynamic bounds
    assert ".websocketUrl=" in app_content
    assert "@token-action=" in app_content
    assert "@aoe-place=" in app_content
    assert "@spell-vfx-triggered=" in app_content
    assert "@confirm-ghost=" in app_content
    assert ".cols=${this.boardCols}" in app_content
    assert ".rows=${this.boardRows}" in app_content
    assert ".atmosphere=${this.atmosphere}" in app_content

    # Expanded socket event handling
    assert "'dice_rolled'" in app_content
    assert "'turn_advanced'" in app_content
    assert "'aoe_placed'" in app_content
    assert "'spell_vfx'" in app_content
    assert "'dm_whisper'" in app_content
