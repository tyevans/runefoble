"""Adaptive stem mixer, manual mood overrides, and ducking router (TASK-0050)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from runefoble_auth.spicedb import SpiceDBClient

from soundscape.aggregate import SoundscapeAggregate
from soundscape.dependencies import (
    check_user_can_control_soundscape,
    get_current_user_id,
    get_or_create_aggregate_id,
    get_or_create_mixer,
    get_soundscape_repo,
    get_spicedb_client,
    publish_soundscape_event,
)
from soundscape.mixer import STEM_PROFILE_WEIGHTS, TACTICAL_FOLEY_CATALOG
from soundscape.models import (
    DuckingRequest,
    MoodOverrideRequest,
    StemVolumeUpdateRequest,
    TensionStatusResponse,
)

router = APIRouter(prefix="/api/v1/soundscape", tags=["Audio Stems & Mixer"])


@router.get(
    "/stems",
    status_code=status.HTTP_200_OK,
    summary="List available audio stems and foley presets",
)
async def list_audio_stems(
    session_id: str = Query(default="default", description="Game session ID"),
) -> dict[str, Any]:
    """Retrieve catalog of stems, presets, and active mixer configuration."""
    mixer = get_or_create_mixer(session_id)
    return {
        "session_id": session_id,
        "available_profiles": list(STEM_PROFILE_WEIGHTS.keys()),
        "stem_layers": ["ambient", "tension", "combat", "boss"],
        "active_profile": mixer.stem_profile,
        "profile_weights": STEM_PROFILE_WEIGHTS,
        "current_stem_gains": mixer.calculate_active_stem_gains(),
        "stem_channels": mixer.channel_volumes,
        "is_ducked": mixer.is_ducked,
        "ducking_attenuation_db": -12.0 if mixer.is_ducked else 0.0,
        "foley_presets": list(TACTICAL_FOLEY_CATALOG.keys()),
    }


@router.post(
    "/stems/volume",
    status_code=status.HTTP_200_OK,
    summary="Update multi-channel stem volume sliders (melody, percussion, drone, ambient)",
)
async def update_stem_volumes(
    request: StemVolumeUpdateRequest,
) -> dict[str, Any]:
    """Adjust individual volume sliders for multi-channel stem tracks."""
    mixer = get_or_create_mixer(request.session_id)
    mixer.update_channel_volumes(request.stem_volumes)
    return {
        "session_id": request.session_id,
        "stem_channels": mixer.channel_volumes,
        "master_volume": mixer.master_volume,
        "effective_gain": mixer.get_effective_gain(),
        "is_ducked": mixer.is_ducked,
    }


@router.post(
    "/override",
    response_model=TensionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually override soundscape mood profile (DM authority)",
)
@router.post(
    "/stems/override",
    response_model=TensionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually override soundscape mood profile (DM authority)",
)
async def override_mood(
    request: MoodOverrideRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> TensionStatusResponse:
    """Manually force soundscape mood/stem profile (Exploration, Tension, Combat, Boss).

    Guarded by SpiceDB Zanzibar authorization (session run_session/control).
    """
    can_override = await check_user_can_control_soundscape(
        user_id=user_id,
        session_id=request.session_id,
        campaign_id=request.campaign_id,
        spicedb=spicedb,
    )
    if not can_override:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: caller lacks Zanzibar permissions to override soundscape mood",
        )

    if request.mood not in STEM_PROFILE_WEIGHTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mood profile '{request.mood}'. Valid: {list(STEM_PROFILE_WEIGHTS.keys())}",
        )

    mixer = get_or_create_mixer(request.session_id)
    mixer.stem_profile = request.mood
    if request.master_volume is not None:
        mixer.master_volume = request.master_volume

    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(request.session_id)
    try:
        agg = await repo.load(agg_id)
    except Exception:
        agg = SoundscapeAggregate(agg_id)

    agg.record_mood_override(
        session_id=request.session_id,
        mood=request.mood,
        overridden_by=user_id or "dm",
    )
    agg.record_track_change(
        session_id=request.session_id,
        track_id=f"track-{request.mood}-override",
        stem_profile=request.mood,
        tension_score=agg.state.tension_score,
        crossfade_duration_ms=1000,
        active_stems=[request.mood],
    )

    events = list(agg.uncommitted_events)
    await repo.save(agg)
    for event in events:
        await publish_soundscape_event(event)

    return TensionStatusResponse(
        session_id=request.session_id,
        tension_score=agg.state.tension_score,
        stem_profile=request.mood,
        active_stems=agg.state.active_stems,
        stem_volumes=mixer.calculate_active_stem_gains(),
        master_volume=mixer.master_volume,
        is_ducked=mixer.is_ducked,
        ducking_attenuation_db=-12.0 if mixer.is_ducked else 0.0,
        effective_gain=mixer.get_effective_gain(),
        manual_override=True,
        override_mood=request.mood,
        recent_cues=agg.state.cues_history,
    )


@router.post(
    "/duck",
    status_code=status.HTTP_200_OK,
    summary="Toggle WebAudio background music ducking (-12dB)",
)
async def toggle_ducking(
    request: DuckingRequest,
) -> dict[str, Any]:
    """Attenuate or restore background audio stems during speech or foley."""
    mixer = get_or_create_mixer(request.session_id)
    mixer.set_ducking(request.is_ducked, reason=request.reason)

    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(request.session_id)
    try:
        agg = await repo.load(agg_id)
    except Exception:
        agg = SoundscapeAggregate(agg_id)

    agg.record_ducking_toggle(
        session_id=request.session_id,
        is_ducked=request.is_ducked,
        attenuation_db=-12.0 if request.is_ducked else 0.0,
        reason=request.reason,
    )
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    for event in events:
        await publish_soundscape_event(event)

    return {
        "session_id": request.session_id,
        "is_ducked": mixer.is_ducked,
        "attenuation_db": -12.0 if mixer.is_ducked else 0.0,
        "effective_gain": mixer.get_effective_gain(),
        "reason": request.reason,
    }
