"""Tactical kinetic spell VFX and WebGL particle animation router."""

from __future__ import annotations

from board_state.dependencies import get_or_create_board, repo
from board_state.models import (
    BoardDecalState,
    CastSpellRequest,
    CastSpellResponse,
    DecayDecalsRequest,
    FinishVFXRequest,
    FinishVFXResponse,
)
from board_state.preview import board_ws_manager
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["vfx"])


def _determine_audio_stinger(archetype: str, spell_name: str, damage_type: str | None) -> str:
    """Select the spatial audio cue corresponding to the spell archetype and element."""
    sp = spell_name.lower()
    dt = (damage_type or "").lower()
    if archetype == "evocation":
        if "lightning" in sp or "lightning" in dt:
            return "evocation_lightning_stinger"
        if "cold" in sp or "frost" in sp or "cold" in dt:
            return "evocation_frost_stinger"
        return "evocation_fireball_stinger"
    if archetype == "abjuration":
        return "abjuration_shield_chime"
    if archetype == "conjuration":
        return "conjuration_portal_drone"
    return "arcane_cast_generic"


@router.post("/api/v1/boards/{session_id}/spells/cast", response_model=CastSpellResponse)
@router.post("/api/v1/boards/{session_id}/vfx/spell", response_model=CastSpellResponse)
async def cast_spell_vfx(session_id: str, req: CastSpellRequest) -> CastSpellResponse:
    """Cast a kinetic spell, calculate WebGL trajectory, radius bloom, decals, and broadcast VFX."""
    board = await get_or_create_board(session_id)

    try:
        anim_id, trajectory, affected_tokens, affected_cells, decal_type = board.cast_spell(
            spell_name=req.spell_name,
            target_x=req.target_x,
            target_y=req.target_y,
            caster_token_id=req.caster_token_id,
            spell_archetype=req.spell_archetype,
            origin_x=req.origin_x,
            origin_y=req.origin_y,
            radius_ft=req.radius_ft,
            damage_dice=req.damage_dice,
            damage_type=req.damage_type,
            theme_palette=req.theme_palette,
        )
        await repo.save(board)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    audio_stinger = _determine_audio_stinger(req.spell_archetype, req.spell_name, req.damage_type)
    ox = (
        req.origin_x
        if req.origin_x is not None
        else (
            board.state.tokens[req.caster_token_id].x
            if req.caster_token_id and req.caster_token_id in board.state.tokens
            else req.target_x
        )
    )
    oy = (
        req.origin_y
        if req.origin_y is not None
        else (
            board.state.tokens[req.caster_token_id].y
            if req.caster_token_id and req.caster_token_id in board.state.tokens
            else req.target_y
        )
    )

    resp = CastSpellResponse(
        animation_id=anim_id,
        session_id=session_id,
        spell_name=req.spell_name,
        spell_archetype=req.spell_archetype,
        caster_token_id=req.caster_token_id,
        origin_x=ox,
        origin_y=oy,
        target_x=req.target_x,
        target_y=req.target_y,
        radius_ft=req.radius_ft,
        trajectory=trajectory,
        affected_token_ids=affected_tokens,
        affected_cells=affected_cells,
        decal_type=decal_type,
        status="launched",
        audio_stinger=audio_stinger,
        duration_ms=450,
    )

    # Broadcast to real-time WebGL particle overlay subscribers
    await board_ws_manager.broadcast(
        session_id,
        {
            "type": "spell_vfx",
            "action": "spell_vfx",
            "status": "launched",
            "session_id": session_id,
            "spell_cast": resp.model_dump(),
        },
    )

    return resp


@router.post("/api/v1/boards/{session_id}/vfx/finish", response_model=FinishVFXResponse)
async def finish_spell_vfx(session_id: str, req: FinishVFXRequest) -> FinishVFXResponse:
    """Record completion of WebGL particle animation."""
    board = await get_or_create_board(session_id)
    board.finish_vfx(
        animation_id=req.animation_id,
        spell_name=req.spell_name,
        target_x=req.target_x,
        target_y=req.target_y,
        duration_ms=req.duration_ms,
    )
    await repo.save(board)

    await board_ws_manager.broadcast(
        session_id,
        {
            "type": "vfx_finished",
            "action": "vfx_finished",
            "status": "finished",
            "session_id": session_id,
            "animation_id": req.animation_id,
            "spell_name": req.spell_name,
        },
    )
    return FinishVFXResponse(animation_id=req.animation_id, status="finished")


@router.get("/api/v1/boards/{session_id}/decals", response_model=list[BoardDecalState])
async def get_board_decals(session_id: str) -> list[BoardDecalState]:
    """Retrieve all active ephemeral decals on the tactical board."""
    board = await get_or_create_board(session_id)
    return board.state.active_decals


@router.post("/api/v1/boards/{session_id}/decals/decay", response_model=list[BoardDecalState])
async def decay_board_decals(session_id: str, req: DecayDecalsRequest) -> list[BoardDecalState]:
    """Decay ephemeral scorched earth / frost decals over rounds."""
    board = await get_or_create_board(session_id)
    board.decay_decals(req.rounds)
    await repo.save(board)
    return board.state.active_decals
