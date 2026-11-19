"""Character Musical Leitmotifs & Adaptive Musical Signatures REST Router (TASK-0102).

Provides frontdoor endpoints for registering character instrument signatures,
triumphant and somber theme profiles, volume envelope configurations,
interactive player auditioning, and real-time active playback inspection.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.models import utc_now

from soundscape.dependencies import (
    CallerId,
    check_user_can_control_soundscape,
    get_principal,
)
from soundscape.leitmotif import (
    TIMBRE_PRESETS,
    ActiveLeitmotifPlayback,
    CharacterLeitmotifProfile,
    LeitmotifEngine,
    LeitmotifTriggerRequest,
)
from soundscape.session_state import (
    load_session_aggregate,
    read_session_state,
    save_session_aggregate,
)

router = APIRouter(
    prefix="/api/v1/soundscape/leitmotif",
    tags=["Character Leitmotifs"],
    dependencies=[Depends(get_principal)],
)


async def check_leitmotif_authorization(
    user_id: str,
    character_id: str,
    session_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBPort,
) -> bool:
    """Enforce Zanzibar permissions for character leitmotif configuration & triggers."""
    # 1. Check if user has edit rights for this character
    can_edit = await check_subject(spicedb, "character", character_id, "edit", user_id)
    if can_edit:
        return True

    # 2. Check session or campaign control/play permissions
    return await check_user_can_control_soundscape(
        user_id=user_id,
        session_id=session_id,
        campaign_id=campaign_id,
        spicedb=spicedb,
    )


@router.get(
    "/timbres",
    status_code=status.HTTP_200_OK,
    summary="List available instrument timbre presets and sample stems",
)
async def list_timbre_presets() -> dict[str, Any]:
    """Return catalog of available instrument signatures (lute, brass, woodwind, strings, synth)."""
    return {
        "presets": TIMBRE_PRESETS,
        "supported_timbres": list(TIMBRE_PRESETS.keys()),
    }


@router.post(
    "/profile",
    response_model=CharacterLeitmotifProfile,
    status_code=status.HTTP_200_OK,
    summary="Configure character musical signature and leitmotif stem URLs",
)
async def configure_character_leitmotif(
    request: CharacterLeitmotifProfile,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
) -> CharacterLeitmotifProfile:
    """Persist and activate character leitmotif configuration.

    Guarded by SpiceDB Zanzibar object authorization (character:edit or session:control).
    """
    authorized = await check_leitmotif_authorization(
        user_id=user_id,
        character_id=request.character_id,
        session_id=request.session_id,
        campaign_id=request.campaign_id,
        spicedb=spicedb,
    )
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient Zanzibar permissions to configure character leitmotif",
        )

    saved_profile = LeitmotifEngine(session_id=request.session_id).register_profile(request)

    agg = await load_session_aggregate(request.session_id)
    agg.record_leitmotif_profile(
        session_id=saved_profile.session_id,
        character_id=saved_profile.character_id,
        character_name=saved_profile.character_name,
        instrument_timbre=saved_profile.instrument_timbre,
        tempo_multiplier=saved_profile.tempo_multiplier,
        triumphant_stem_url=saved_profile.triumphant_stem_url or "",
        somber_stem_url=saved_profile.somber_stem_url or "",
        volume_gain=saved_profile.volume_gain,
        attack_ms=saved_profile.attack_ms,
        release_ms=saved_profile.release_ms,
        duration_ms=saved_profile.duration_ms,
    )
    await save_session_aggregate(agg)

    return saved_profile


@router.get(
    "/profile/{character_id}",
    response_model=CharacterLeitmotifProfile,
    status_code=status.HTTP_200_OK,
    summary="Get character leitmotif configuration profile",
)
async def get_character_leitmotif_profile(
    character_id: str,
    session_id: str = Query(default="default", description="Associated session ID"),
) -> CharacterLeitmotifProfile:
    """Retrieve active or persisted configuration for character."""
    state = await read_session_state(session_id)
    data = state.character_profiles.get(character_id)
    profile = CharacterLeitmotifProfile(**data) if data else None

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leitmotif profile for character '{character_id}' not found",
        )
    return profile


@router.post(
    "/trigger",
    response_model=ActiveLeitmotifPlayback,
    status_code=status.HTTP_200_OK,
    summary="Trigger or audition character musical leitmotif stinger",
)
async def trigger_character_leitmotif(
    request: LeitmotifTriggerRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
) -> ActiveLeitmotifPlayback:
    """Trigger dynamic stem stinger or audition character leitmotif.

    Guarded by SpiceDB Zanzibar authorization.
    """
    authorized = await check_leitmotif_authorization(
        user_id=user_id,
        character_id=request.character_id,
        session_id=request.session_id,
        campaign_id=request.campaign_id,
        spicedb=spicedb,
    )
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient Zanzibar permissions to trigger character leitmotif",
        )

    agg = await load_session_aggregate(request.session_id)
    engine = LeitmotifEngine.from_state(request.session_id, agg.state, utc_now())
    playback = engine.trigger_leitmotif(
        character_id=request.character_id,
        motif_type=request.motif_type,
        trigger_reason=request.trigger_reason,
        character_name=request.character_name,
        volume_gain=request.volume_gain,
    )

    agg.record_leitmotif_trigger(
        session_id=playback.session_id,
        character_id=playback.character_id,
        character_name=playback.character_name,
        motif_type=playback.motif_type,
        instrument_timbre=playback.instrument_timbre,
        stem_url=playback.stem_url,
        tempo_multiplier=playback.tempo_multiplier,
        volume_gain=playback.volume_gain,
        attack_ms=playback.attack_ms,
        release_ms=playback.release_ms,
        duration_ms=playback.duration_ms,
        duck_music=False,
        trigger_reason=playback.trigger_reason,
        playback_id=playback.playback_id,
        triggered_at=playback.triggered_at,
    )
    await save_session_aggregate(agg)

    return playback


@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    summary="Get currently active leitmotif layer and envelope state",
)
async def get_active_leitmotif(
    session_id: str = Query(default="default", description="Game session ID"),
) -> dict[str, Any]:
    """Inspect active leitmotif playback, envelope stage, and voice ducking attenuation."""
    state = await read_session_state(session_id)
    engine = LeitmotifEngine.from_state(session_id, state, utc_now())
    playback = engine.get_active_status()
    return {
        "session_id": session_id,
        "is_playing": playback is not None,
        "active_leitmotif": playback.model_dump() if playback else None,
        "is_ducked": engine.is_ducked,
    }
