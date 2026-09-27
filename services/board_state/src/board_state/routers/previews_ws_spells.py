"""Tactical board WebSocket message handlers for kinetic spell VFX and animations."""

from __future__ import annotations

from typing import Any

from board_state.aggregate import BoardAggregate
from board_state.dependencies import repo
from board_state.preview import board_ws_manager


async def handle_ws_spell(
    session_id: str, action: str, data: dict[str, Any], board: BoardAggregate
) -> bool:
    """Handle cast_spell and spell_vfx messages over WebSocket."""
    if not (
        action in ("cast_spell", "spell_vfx", "SpellCast")
        or (
            action == "SpeechIntentParsed"
            and (
                data.get("action_type") == "cast_spell"
                or data.get("parameters", {}).get("action") == "cast_spell"
            )
        )
    ):
        return False

    p = data.get("parameters") or {}
    sp_name = data.get("spell_name") or data.get("spell") or p.get("spell", "Fireball")
    tx = (
        data.get("target_x")
        if data.get("target_x") is not None
        else data.get("to_x")
        if data.get("to_x") is not None
        else p.get("target_x", 0)
    )
    ty = (
        data.get("target_y")
        if data.get("target_y") is not None
        else data.get("to_y")
        if data.get("to_y") is not None
        else p.get("target_y", 0)
    )
    caster_id = data.get("caster_token_id") or data.get("token_id")
    if not caster_id and (spk := data.get("speaker_name")):
        caster_id = next(
            (
                tok.token_id
                for tok in board.state.tokens.values()
                if tok.name.lower() == spk.lower()
            ),
            None,
        )
    arch = data.get("spell_archetype") or p.get("spell_archetype", "evocation")
    rad = int(data.get("radius_ft") or p.get("radius_ft", 20))
    aid, traj, aff_t, aff_c, decal = board.cast_spell(
        spell_name=sp_name,
        target_x=int(tx),
        target_y=int(ty),
        caster_token_id=caster_id,
        spell_archetype=arch,
        origin_x=data.get("origin_x"),
        origin_y=data.get("origin_y"),
        radius_ft=rad,
        damage_type=data.get("damage_type") or p.get("damage_type"),
    )
    await repo.save(board)
    await board_ws_manager.broadcast(
        session_id,
        {
            "type": "spell_vfx",
            "action": "spell_vfx",
            "status": "launched",
            "session_id": session_id,
            "animation_id": aid,
            "spell_name": sp_name,
            "spell_archetype": arch,
            "caster_token_id": caster_id,
            "target_x": int(tx),
            "target_y": int(ty),
            "radius_ft": rad,
            "trajectory": traj,
            "affected_token_ids": aff_t,
            "affected_cells": aff_c,
            "decal_type": decal,
        },
    )
    return True


__all__ = ["handle_ws_spell"]
