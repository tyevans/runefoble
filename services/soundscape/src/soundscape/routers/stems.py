"""Adaptive stem mixer, manual mood overrides, and ducking router (TASK-0050)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.models import utc_now

from soundscape.dependencies import (
    CallerId,
    check_user_can_control_soundscape,
    get_principal,
)
from soundscape.mixer import (
    STEM_PROFILE_WEIGHTS,
    TACTICAL_FOLEY_CATALOG,
    merged_channel_volumes,
)
from soundscape.models import (
    DuckingRequest,
    MoodOverrideRequest,
    StemVolumeUpdateRequest,
    TensionStatusResponse,
)
from soundscape.session_state import (
    load_session_aggregate,
    read_session_state,
    save_session_aggregate,
    tension_status,
)

router = APIRouter(
    prefix="/api/v1/soundscape", tags=["Audio Stems & Mixer"], dependencies=[Depends(get_principal)]
)

DUCKING_ATTENUATION_DB = -12.0


@router.get(
    "/stems",
    status_code=status.HTTP_200_OK,
    summary="List available audio stems and foley presets",
)
async def list_audio_stems(
    session_id: str = Query(default="default", description="Game session ID"),
) -> dict[str, Any]:
    """Retrieve catalog of stems, presets, and active mixer configuration."""
    state = await read_session_state(session_id)
    mixer = state.mixer_at(utc_now())
    return {
        "session_id": session_id,
        "available_profiles": list(STEM_PROFILE_WEIGHTS.keys()),
        "stem_layers": ["ambient", "tension", "combat", "boss"],
        "active_profile": mixer.stem_profile,
        "profile_weights": STEM_PROFILE_WEIGHTS,
        "current_stem_gains": mixer.calculate_active_stem_gains(),
        "stem_channels": mixer.channel_volumes,
        "is_ducked": mixer.is_ducked,
        "ducking_attenuation_db": DUCKING_ATTENUATION_DB if mixer.is_ducked else 0.0,
        "foley_presets": list(TACTICAL_FOLEY_CATALOG.keys()),
    }


@router.post(
    "/stems/volume",
    status_code=status.HTTP_200_OK,
    summary="Update multi-channel stem volume sliders (melody, percussion, drone, ambient)",
)
async def update_stem_volumes(
    request: StemVolumeUpdateRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Adjust individual volume sliders for multi-channel stem tracks (session control)."""
    allowed = await check_user_can_control_soundscape(
        user_id=user_id,
        session_id=request.session_id,
        campaign_id=request.campaign_id,
        spicedb=spicedb,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: caller lacks Zanzibar permissions to adjust soundscape stems",
        )
    agg = await load_session_aggregate(request.session_id)
    agg.record_channel_volumes(
        request.session_id,
        merged_channel_volumes(agg.state.channel_volumes, request.stem_volumes),
    )
    await save_session_aggregate(agg)
    mixer = agg.state.mixer_at(utc_now())
    return {
        "session_id": request.session_id,
        "stem_channels": mixer.channel_volumes,
        "master_volume": mixer.master_volume,
        "effective_gain": mixer.get_effective_gain(),
        "is_ducked": mixer.is_ducked,
    }


@router.post(
    "/stems/override",
    response_model=TensionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually override soundscape mood profile (DM authority)",
)
async def override_mood(
    request: MoodOverrideRequest,
    user_id: CallerId,
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

    agg = await load_session_aggregate(request.session_id)
    agg.record_stem_profile_overridden(
        session_id=request.session_id,
        mood=request.mood,
        overridden_by=user_id,
    )
    agg.record_track_change(
        session_id=request.session_id,
        track_id=f"track-{request.mood}-override",
        stem_profile=request.mood,
        tension_score=agg.state.tension_score,
        crossfade_duration_ms=1000,
        active_stems=[request.mood],
    )
    if request.master_volume is not None:
        agg.record_master_volume(request.session_id, request.master_volume)
    await save_session_aggregate(agg)
    return tension_status(request.session_id, agg.state)


@router.post(
    "/duck",
    status_code=status.HTTP_200_OK,
    summary="Engage or release WebAudio background music ducking (-12dB)",
)
async def toggle_ducking(
    request: DuckingRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Attenuate background stems for a stored duration, or release a duck (session control).

    `is_ducked: true` records DuckingEngaged with `duration_ms`. `is_ducked: false` records
    DuckingReleased and ends any engagement at once.
    """
    allowed = await check_user_can_control_soundscape(
        user_id=user_id,
        session_id=request.session_id,
        campaign_id=None,
        spicedb=spicedb,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: caller lacks Zanzibar permissions to duck soundscape audio",
        )
    agg = await load_session_aggregate(request.session_id)
    if request.is_ducked:
        agg.record_ducking_engaged(
            session_id=request.session_id,
            reason=request.reason,
            duration_ms=request.duration_ms,
            attenuation_db=DUCKING_ATTENUATION_DB,
        )
    else:
        agg.record_ducking_released(session_id=request.session_id, reason=request.reason)
    await save_session_aggregate(agg)

    mixer = agg.state.mixer_at(utc_now())
    return {
        "session_id": request.session_id,
        "is_ducked": mixer.is_ducked,
        "attenuation_db": DUCKING_ATTENUATION_DB if mixer.is_ducked else 0.0,
        "effective_gain": mixer.get_effective_gain(),
        "reason": request.reason,
    }
