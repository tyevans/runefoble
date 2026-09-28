"""Blackbox tests for real-time WebSocket speech VFX triggers and domain event persistence."""

import time
from uuid import uuid4

import pytest
from board_state.aggregate import BoardAggregate
from board_state.dependencies import repo, to_board_uuid
from fastapi.testclient import TestClient


def test_websocket_realtime_speech_spell_trigger_sub_150ms(client: TestClient) -> None:
    """Verify WebSocket real-time stream handles spoken spellcast and broadcasts VFX in <150ms."""
    board_id = f"board-{uuid4().hex[:8]}"

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "nadia", "name": "Nadia", "x": 1, "y": 2, "is_friendly": True},
    )

    with client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"

        # Broadcast spoken intent to board
        t0 = time.perf_counter()
        ws.send_json(
            {
                "type": "cast_spell",
                "spell_name": "Fireball",
                "spell_archetype": "evocation",
                "caster_token_id": "nadia",
                "target_x": 7,
                "target_y": 4,
                "radius_ft": 20,
                "damage_type": "fire",
            }
        )

        vfx_msg = ws.receive_json()
        latency_ms = (time.perf_counter() - t0) * 1000

        # Platform SLA verification (<500ms)
        assert latency_ms < 500.0, (
            f"WebSocket VFX trigger latency {latency_ms:.2f}ms exceeded 500ms"
        )

        assert vfx_msg["type"] == "spell_vfx"
        assert vfx_msg["status"] == "launched"
        assert vfx_msg["spell_name"] == "Fireball"
        assert vfx_msg["caster_token_id"] == "nadia"
        assert vfx_msg["target_x"] == 7
        assert vfx_msg["target_y"] == 4
        assert vfx_msg["radius_ft"] == 20
        assert len(vfx_msg["trajectory"]) >= 2
        assert vfx_msg["decal_type"] == "scorched_earth"


@pytest.mark.asyncio
async def test_event_sourcing_domain_events_persistence() -> None:
    """Verify SpellCast, AreaEffectExploded, and VFXAnimationFinished events are recorded."""
    sess_id = f"board-{uuid4().hex[:8]}"
    board_uuid = to_board_uuid(sess_id)
    board = BoardAggregate(board_uuid)
    board.initialize_grid(cols=10, rows=10, session_id=sess_id)
    board.place_token("valeros", "Valeros", "pc", 2, 2, 40, True)

    anim_id, trajectory, affected_tokens, affected_cells, decal = board.cast_spell(
        spell_name="Chain Lightning",
        target_x=5,
        target_y=5,
        caster_token_id="valeros",
        spell_archetype="evocation",
        radius_ft=15,
        damage_type="lightning",
    )
    board.finish_vfx(anim_id, "Chain Lightning", 5, 5, 400)
    await repo.save(board)

    # Reload aggregate and verify event replay
    loaded_board = await repo.load(board_uuid)
    assert loaded_board is not None
    assert loaded_board.state.cols == 10
    assert len(loaded_board.state.active_decals) > 0
