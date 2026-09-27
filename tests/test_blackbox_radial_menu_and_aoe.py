"""Blackbox tests for Radial Token Action Menu & Rotatable AoE Spell Templates.

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0006: Redis Streams Event Bus (TokenActionExecuted & AoETemplatePlaced)
- ADR-0013: Microfrontend Architecture
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup (strictly HTTP & WebSockets)
"""

from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(board_app)


def test_radial_token_action_execution_frontdoor(client):
    """Verify radial token actions (Dodge, Dash, Attack, Disengage, Cast) via public HTTP routes."""
    board_id = f"board-{uuid4().hex[:8]}"

    # Setup board and token via frontdoors
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 2, "y": 2, "is_friendly": True},
    )
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "goblin-1", "name": "Goblin", "x": 3, "y": 2, "is_friendly": False},
    )

    # 1. Execute "dodge" action
    res_dodge = client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/action",
        json={"action": "dodge", "initiated_by": "player"},
    )
    assert res_dodge.status_code == 200
    dodge_data = res_dodge.json()
    assert dodge_data["token_id"] == "valeros"
    assert dodge_data["action"] == "dodge"
    assert dodge_data["status"] == "executed"

    # Verify state reflects active action
    board_state = client.get(f"/api/v1/boards/{board_id}").json()
    assert board_state["tokens"]["valeros"]["active_action"] == "dodge"

    # 2. Execute "attack" action with target
    res_attack = client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/action",
        json={
            "action": "attack",
            "target_token_id": "goblin-1",
            "details": {"weapon": "Longsword", "damage_type": "slashing"},
        },
    )
    assert res_attack.status_code == 200
    attack_data = res_attack.json()
    assert attack_data["action"] == "attack"
    assert "goblin-1" in attack_data["target_token_ids"]
    assert attack_data["details"]["weapon"] == "Longsword"

    # 3. Execute "dash" via root action endpoint
    res_dash = client.post(
        f"/api/v1/boards/{board_id}/actions",
        json={"token_id": "valeros", "action": "dash"},
    )
    assert res_dash.status_code == 200
    assert res_dash.json()["action"] == "dash"

    # 4. Unknown token returns 404
    res_unknown = client.post(
        f"/api/v1/boards/{board_id}/tokens/nonexistent/action",
        json={"action": "dodge"},
    )
    assert res_unknown.status_code == 404


def test_aoe_rotatable_cone_calculations_and_angle_snapping(client):
    """Verify 15ft cone mathematical calculations, target tokens, and 15-degree angle snapping."""
    board_id = f"board-{uuid4().hex[:8]}"
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})

    # Place caster Marcus at (2, 2)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "marcus", "name": "Marcus", "x": 2, "y": 2, "is_friendly": True},
    )
    # Target East at (4, 2)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "goblin-east", "name": "Goblin East", "x": 4, "y": 2},
    )
    # Target South at (2, 4)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "goblin-south", "name": "Goblin South", "x": 2, "y": 4},
    )

    # 1. Cone pointing East (0 degrees, raw 7 degrees snaps to 0)
    res_east = client.post(
        f"/api/v1/boards/{board_id}/aoe/evaluate",
        json={
            "caster_token_id": "marcus",
            "shape": "cone",
            "origin_x": 2.5,
            "origin_y": 2.5,
            "direction_deg": 7.0,  # Should snap to 0.0
            "radius_ft": 15.0,
            "spell_name": "Burning Hands",
        },
    )
    assert res_east.status_code == 200
    data_east = res_east.json()
    assert data_east["direction_deg"] == 0.0  # Snapped to 0 deg
    assert "goblin-east" in data_east["affected_token_ids"]
    assert "goblin-south" not in data_east["affected_token_ids"]
    assert len(data_east["affected_cells"]) > 0

    # 2. Rotate cone South (raw 82 degrees snaps to 90 degrees)
    res_south = client.post(
        f"/api/v1/boards/{board_id}/aoe/evaluate",
        json={
            "caster_token_id": "marcus",
            "shape": "cone",
            "origin_x": 2.5,
            "origin_y": 2.5,
            "direction_deg": 86.0,  # Should snap to 90.0
            "radius_ft": 15.0,
            "spell_name": "Burning Hands",
        },
    )
    assert res_south.status_code == 200
    data_south = res_south.json()
    assert data_south["direction_deg"] == 90.0  # Snapped to 90 deg
    assert "goblin-south" in data_south["affected_token_ids"]
    assert "goblin-east" not in data_south["affected_token_ids"]


def test_aoe_sphere_and_line_geometry_evaluations(client):
    """Verify spherical radius and line projection intersection testing."""
    board_id = f"board-{uuid4().hex[:8]}"
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})

    # Center token at (5, 5)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "center-tok", "name": "Center", "x": 5, "y": 5},
    )
    # Near token at (6, 5) (5ft away)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "near-tok", "name": "Near", "x": 6, "y": 5},
    )
    # Far token at (11, 11) (way outside 20ft sphere)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "far-tok", "name": "Far", "x": 11, "y": 11},
    )

    # 1. 20-ft sphere centered at (5.5, 5.5)
    res_sphere = client.post(
        f"/api/v1/boards/{board_id}/aoe/evaluate",
        json={
            "shape": "sphere",
            "origin_x": 5.5,
            "origin_y": 5.5,
            "radius_ft": 20.0,
            "spell_name": "Fireball",
        },
    )
    assert res_sphere.status_code == 200
    sphere_data = res_sphere.json()
    assert "center-tok" in sphere_data["affected_token_ids"]
    assert "near-tok" in sphere_data["affected_token_ids"]
    assert "far-tok" not in sphere_data["affected_token_ids"]

    # 2. 5ft x 30ft Line starting at (0.0, 5.5) pointing East (0 deg)
    res_line = client.post(
        f"/api/v1/boards/{board_id}/aoe/evaluate",
        json={
            "shape": "line",
            "origin_x": 0.0,
            "origin_y": 5.5,
            "direction_deg": 0.0,
            "length_ft": 30.0,
            "width_ft": 5.0,
            "spell_name": "Lightning Bolt",
        },
    )
    assert res_line.status_code == 200
    line_data = res_line.json()
    # (5, 5) is at distance ~27.5 ft East from (0, 5.5), within 30ft line
    assert "center-tok" in line_data["affected_token_ids"]
    assert "far-tok" not in line_data["affected_token_ids"]


def test_aoe_template_placement_and_lifecycle(client):
    """Verify AoE template placement, persistence in aggregate, listing, and deletion."""
    board_id = f"board-{uuid4().hex[:8]}"
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "tok-1", "name": "Valeros", "x": 3, "y": 3},
    )

    # Place AoE template
    place_res = client.post(
        f"/api/v1/boards/{board_id}/aoe/place",
        json={
            "template_id": "aoe-1",
            "shape": "sphere",
            "origin_x": 3.5,
            "origin_y": 3.5,
            "radius_ft": 10.0,
            "spell_name": "Faerie Fire",
        },
    )
    assert place_res.status_code == 200
    placed = place_res.json()
    assert placed["template_id"] == "aoe-1"
    assert "tok-1" in placed["affected_token_ids"]

    # Verify template is in board aggregate active templates
    list_res = client.get(f"/api/v1/boards/{board_id}/aoe")
    assert list_res.status_code == 200
    templates = list_res.json()
    assert len(templates) == 1
    assert templates[0]["template_id"] == "aoe-1"

    # Delete template
    del_res = client.delete(f"/api/v1/boards/{board_id}/aoe/aoe-1")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "removed"

    # Verify removal
    list_after = client.get(f"/api/v1/boards/{board_id}/aoe").json()
    assert len(list_after) == 0


def test_websocket_radial_action_and_aoe_streaming(client):
    """Verify real-time WebSocket messaging for radial token actions and live AoE calculations."""
    board_id = f"board-{uuid4().hex[:8]}"
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "kyra", "name": "Kyra", "x": 4, "y": 4, "is_friendly": True},
    )

    with client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        handshake = ws.receive_json()
        assert handshake["type"] == "connected"

        # 1. Send radial token action via WebSocket
        ws.send_json(
            {
                "action": "token_action",
                "token_id": "kyra",
                "token_action": "cast",
                "details": {"spell": "Sacred Flame"},
            }
        )
        msg_action = ws.receive_json()
        assert msg_action["type"] == "token_action_executed"
        assert msg_action["action"] == "cast"
        assert msg_action["token_id"] == "kyra"

        # 2. Live AoE preview streaming via WebSocket
        ws.send_json(
            {
                "action": "aoe_preview",
                "shape": "cone",
                "origin_x": 4.5,
                "origin_y": 4.5,
                "direction_deg": 45.0,
                "radius_ft": 15.0,
                "spell_name": "Sacred Flame",
            }
        )
        msg_preview = ws.receive_json()
        assert msg_preview["type"] == "aoe_preview"
        assert msg_preview["template"]["shape"] == "cone"
        assert "kyra" in msg_preview["template"]["affected_token_ids"]

        # 3. Confirm AoE placement via WebSocket
        ws.send_json(
            {
                "action": "aoe_place",
                "template_id": "aoe-ws-1",
                "shape": "sphere",
                "origin_x": 4.5,
                "origin_y": 4.5,
                "radius_ft": 10.0,
            }
        )
        msg_placed = ws.receive_json()
        assert msg_placed["type"] == "aoe_template_placed"
        assert msg_placed["template"]["template_id"] == "aoe-ws-1"
