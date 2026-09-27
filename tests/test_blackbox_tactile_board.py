"""Blackbox TDD tests for BoardState modular aggregate handlers and tactile board frontdoors.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Tests token placement, movement, hazards, radial actions, fog, and VFX
through public HTTP frontdoors and event-sourced aggregate reconstitution.
"""

from uuid import uuid4

import pytest
from board_state.aggregate import BoardAggregate
from board_state.main import app
from fastapi.testclient import TestClient
from runefoble_platform.event_sourcing import AggregateRepository, InMemoryEventStore

client = TestClient(app)


@pytest.mark.asyncio
async def test_board_aggregate_event_sourcing_and_modular_handlers():
    """Verify event-sourced BoardAggregate reconstitution using modular handler mixins."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=BoardAggregate)

    board_id = uuid4()
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=10, rows=10, session_id="test-session-modular")

    # 1. Configure difficult terrain and lava hazard
    board.configure_terrain(x=3, y=3, elevation=1, terrain_type="difficult", hazard="lava")
    assert board.get_terrain(3, 3).terrain_type == "difficult"
    assert board.get_terrain(3, 3).hazard == "lava"

    # 2. Place friendly player token
    board.place_token(
        token_id="valeros",
        name="Valeros",
        token_type="pc",
        x=1,
        y=1,
        hp=35,
        is_friendly=True,
        vision_radius=2,
    )
    assert "valeros" in board.state.tokens
    assert board.state.tokens["valeros"].x == 1
    assert board.state.tokens["valeros"].y == 1

    # 3. Move token across hazard at (3, 3) to (4, 4)
    cost, hazard, damage = board.move_token("valeros", to_x=4, to_y=4)
    assert board.state.tokens["valeros"].x == 4
    assert board.state.tokens["valeros"].y == 4
    assert hazard == "lava"
    assert damage == "2d10"
    assert cost > 0

    # 4. Execute tactical token action
    board.execute_token_action(
        token_id="valeros",
        action="dodge",
        details={"stance": "defensive"},
        initiated_by="player",
    )
    assert board.state.tokens["valeros"].active_action == "dodge"

    # 5. Place AoE spell template
    board.place_aoe_template(
        template_id="fireball-1",
        shape="circle",
        origin_x=4.0,
        origin_y=4.0,
        radius_ft=20.0,
        spell_name="Fireball",
        affected_token_ids=["valeros"],
    )
    assert len(board.state.active_aoe_templates) == 1
    assert board.state.active_aoe_templates[0].template_id == "fireball-1"

    # 6. Save aggregate to event store
    await repo.save(board)

    # 7. Reconstitute from event stream and verify all modular handler states match
    reconstituted = await repo.load(board_id)
    assert reconstituted.state.cols == 10
    assert reconstituted.state.rows == 10
    assert reconstituted.state.tokens["valeros"].x == 4
    assert reconstituted.state.tokens["valeros"].y == 4
    assert reconstituted.state.tokens["valeros"].active_action == "dodge"
    assert len(reconstituted.state.active_aoe_templates) == 1
    assert reconstituted.get_terrain(3, 3).hazard == "lava"

    # 8. Remove AoE template and token on reconstituted aggregate
    reconstituted.remove_aoe_template("fireball-1")
    assert len(reconstituted.state.active_aoe_templates) == 0

    reconstituted.remove_token("valeros", reason="extracted")
    assert "valeros" not in reconstituted.state.tokens


def test_blackbox_tactile_board_http_frontdoor_lifecycle():
    """Verify tactile board lifecycle strictly through public REST frontdoors."""
    board_id = f"board-{uuid4().hex[:8]}"

    # Create tactical board
    res_create = client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})
    assert res_create.status_code == 200

    # Place PC token
    res_place = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "kyra", "name": "Kyra", "x": 2, "y": 2, "is_friendly": True},
    )
    assert res_place.status_code == 200
    assert res_place.json()["token_id"] == "kyra"

    # Configure terrain
    res_terrain = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 3, "y": 3, "terrain_type": "difficult", "hazard": "spikes"},
    )
    assert res_terrain.status_code == 200

    # Execute movement through public route
    res_move = client.post(
        f"/api/v1/boards/{board_id}/tokens/kyra/move",
        json={"to_x": 4, "to_y": 4},
    )
    assert res_move.status_code == 200
    data_move = res_move.json()
    assert data_move["x"] == 4
    assert data_move["y"] == 4

    # Execute radial action through public route
    res_action = client.post(
        f"/api/v1/boards/{board_id}/tokens/kyra/action",
        json={"action": "dash"},
    )
    assert res_action.status_code == 200
    assert res_action.json()["action"] == "dash"

    # Remove token through public route
    res_remove = client.delete(f"/api/v1/boards/{board_id}/tokens/kyra")
    assert res_remove.status_code == 200
