"""Encounter tension status and calculation router (TASK-0050)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.port import SpiceDBPort

from soundscape.dependencies import (
    CallerId,
    check_user_can_control_soundscape,
    get_principal,
)
from soundscape.models import TensionCalculationRequest, TensionStatusResponse
from soundscape.scoring import calculate_encounter_tension, derive_stem_profile
from soundscape.session_state import (
    load_session_aggregate,
    read_session_state,
    save_session_aggregate,
    tension_status,
)

router = APIRouter(
    prefix="/api/v1/soundscape", tags=["Tension"], dependencies=[Depends(get_principal)]
)


@router.get(
    "/tension",
    response_model=TensionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current session encounter tension and stem profiles",
)
async def get_tension_status(
    session_id: str = Query(default="default", description="Game session ID"),
) -> TensionStatusResponse:
    """Retrieve current session tension score, active stems, and effective gain levels."""
    state = await read_session_state(session_id)
    return tension_status(session_id, state)


@router.post(
    "/tension/calculate",
    response_model=TensionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate and apply encounter tension score",
)
async def calculate_tension(
    request: TensionCalculationRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
) -> TensionStatusResponse:
    """Compute tension index (0-100) and adaptively update musical stems (session control)."""
    allowed = await check_user_can_control_soundscape(
        user_id=user_id,
        session_id=request.session_id,
        campaign_id=request.campaign_id,
        spicedb=spicedb,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: caller lacks Zanzibar permissions to calculate encounter tension",
        )
    tension_score = calculate_encounter_tension(
        combat_active=request.combat_active,
        combat_round=request.combat_round,
        enemy_cr_balance=request.enemy_cr_balance,
        lowest_party_health_ratio=request.lowest_party_health_ratio,
    )
    derived_profile = derive_stem_profile(tension_score)

    agg = await load_session_aggregate(request.session_id)
    old_profile = agg.state.stem_profile
    agg.record_tension_update(
        session_id=request.session_id,
        tension_score=tension_score,
        stem_profile=derived_profile,
        combat_round=request.combat_round,
        enemy_cr_balance=request.enemy_cr_balance,
        lowest_health_ratio=request.lowest_party_health_ratio,
        combat_active=request.combat_active,
    )
    if not agg.state.manual_override and derived_profile != old_profile:
        agg.record_track_change(
            session_id=request.session_id,
            track_id=f"track-{derived_profile}-01",
            stem_profile=derived_profile,
            tension_score=tension_score,
            crossfade_duration_ms=1500,
            active_stems=[derived_profile],
        )
    await save_session_aggregate(agg)
    return tension_status(request.session_id, agg.state)
