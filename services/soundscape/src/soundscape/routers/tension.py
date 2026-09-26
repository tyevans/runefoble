"""Encounter tension status and calculation router (TASK-0050)."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from soundscape.aggregate import SoundscapeAggregate
from soundscape.dependencies import (
    get_or_create_aggregate_id,
    get_or_create_mixer,
    get_soundscape_repo,
    publish_soundscape_event,
)
from soundscape.models import TensionCalculationRequest, TensionStatusResponse
from soundscape.scoring import calculate_encounter_tension, derive_stem_profile

router = APIRouter(prefix="/api/v1/soundscape", tags=["Tension"])


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
    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(session_id)
    try:
        agg = await repo.load(agg_id)
    except Exception:
        agg = None
    mixer = get_or_create_mixer(session_id)

    tension_score = agg.state.tension_score if agg else 10
    stem_profile = agg.state.stem_profile if agg else mixer.stem_profile
    active_stems = agg.state.active_stems if agg else [stem_profile]
    stem_volumes = mixer.calculate_active_stem_gains()
    effective_gain = mixer.get_effective_gain()
    manual_override = agg.state.manual_override if agg else False
    override_mood = agg.state.override_mood if agg else None
    cues_history = agg.state.cues_history if agg else []

    return TensionStatusResponse(
        session_id=session_id,
        tension_score=tension_score,
        stem_profile=stem_profile,
        active_stems=active_stems,
        stem_volumes=stem_volumes,
        master_volume=mixer.master_volume,
        is_ducked=mixer.is_ducked,
        ducking_attenuation_db=-12.0 if mixer.is_ducked else 0.0,
        effective_gain=effective_gain,
        manual_override=manual_override,
        override_mood=override_mood,
        recent_cues=cues_history,
    )


@router.post(
    "/tension/calculate",
    response_model=TensionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate and apply encounter tension score",
)
async def calculate_tension(
    request: TensionCalculationRequest,
) -> TensionStatusResponse:
    """Compute tension index (0-100) and adaptively update musical stems."""
    tension_score = calculate_encounter_tension(
        combat_active=request.combat_active,
        combat_round=request.combat_round,
        enemy_cr_balance=request.enemy_cr_balance,
        lowest_party_health_ratio=request.lowest_party_health_ratio,
    )
    derived_profile = derive_stem_profile(tension_score)

    mixer = get_or_create_mixer(request.session_id)
    old_profile = mixer.stem_profile

    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(request.session_id)
    try:
        agg = await repo.load(agg_id)
    except Exception:
        agg = SoundscapeAggregate(agg_id)

    agg.record_tension_update(
        session_id=request.session_id,
        tension_score=tension_score,
        stem_profile=derived_profile,
        combat_round=request.combat_round,
        enemy_cr_balance=request.enemy_cr_balance,
        lowest_health_ratio=request.lowest_party_health_ratio,
    )

    if not agg.state.manual_override:
        mixer.stem_profile = derived_profile
        if derived_profile != old_profile:
            agg.record_track_change(
                session_id=request.session_id,
                track_id=f"track-{derived_profile}-01",
                stem_profile=derived_profile,
                tension_score=tension_score,
                crossfade_duration_ms=1500,
                active_stems=[derived_profile],
            )

    events = list(agg.uncommitted_events)
    await repo.save(agg)
    for event in events:
        await publish_soundscape_event(event)

    effective_profile = agg.state.stem_profile
    return TensionStatusResponse(
        session_id=request.session_id,
        tension_score=tension_score,
        stem_profile=effective_profile,
        active_stems=agg.state.active_stems,
        stem_volumes=mixer.calculate_active_stem_gains(),
        master_volume=mixer.master_volume,
        is_ducked=mixer.is_ducked,
        ducking_attenuation_db=-12.0 if mixer.is_ducked else 0.0,
        effective_gain=mixer.get_effective_gain(),
        manual_override=agg.state.manual_override,
        override_mood=agg.state.override_mood,
        recent_cues=agg.state.cues_history,
    )
