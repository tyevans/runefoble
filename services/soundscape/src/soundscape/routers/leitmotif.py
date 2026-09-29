"""Character Musical Leitmotifs & Adaptive Musical Signatures REST Router (TASK-0102).

Provides frontdoor endpoints for registering character instrument signatures,
triumphant and somber theme profiles, volume envelope configurations,
interactive player auditioning, and real-time active playback inspection.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from runefoble_auth.spicedb import SpiceDBClient

from soundscape.aggregate import SoundscapeAggregate
from soundscape.dependencies import (
    check_user_can_control_soundscape,
    get_current_user_id,
    get_or_create_aggregate_id,
    get_or_create_leitmotif_engine,
    get_soundscape_repo,
    get_spicedb_client,
    publish_soundscape_event,
)
from soundscape.leitmotif import (
    TIMBRE_PRESETS,
    ActiveLeitmotifPlayback,
    CharacterLeitmotifProfile,
    LeitmotifTriggerRequest,
)

router = APIRouter(prefix="/api/v1/soundscape/leitmotif", tags=["Character Leitmotifs"])


async def check_leitmotif_authorization(
    user_id: str | None,
    character_id: str,
    session_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient,
) -> bool:
    """Enforce Zanzibar permissions for character leitmotif configuration & triggers."""
    if not user_id:
        return True

    # 1. Check if user has edit rights for this character
    try:
        can_edit = await spicedb.check_permission(
            resource_type="character",
            resource_id=character_id,
            permission="edit",
            subject_type="user",
            subject_id=user_id,
        )
        if can_edit:
            return True
    except Exception:
        pass

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
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
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

    engine = get_or_create_leitmotif_engine(request.session_id)
    saved_profile = engine.register_profile(request)

    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(request.session_id)
    try:
        agg = await repo.load(agg_id)
    except Exception:
        agg = SoundscapeAggregate(agg_id)

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
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    for ev in events:
        await publish_soundscape_event(ev)

    return saved_profile


@router.get(
    "/{character_id}",
    response_model=CharacterLeitmotifProfile,
    status_code=status.HTTP_200_OK,
    summary="Get character leitmotif configuration profile",
)
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
    engine = get_or_create_leitmotif_engine(session_id)
    profile = engine.get_profile(character_id)
    if not profile:
        # Check aggregate state
        repo = get_soundscape_repo()
        agg_id = get_or_create_aggregate_id(session_id)
        try:
            agg = await repo.load(agg_id)
            if agg and character_id in agg.state.character_profiles:
                data = agg.state.character_profiles[character_id]
                profile = CharacterLeitmotifProfile(**data)
                engine.register_profile(profile)
        except Exception:
            pass

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
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
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

    engine = get_or_create_leitmotif_engine(request.session_id)
    playback = engine.trigger_leitmotif(
        character_id=request.character_id,
        motif_type=request.motif_type,
        trigger_reason=request.trigger_reason,
        character_name=request.character_name,
        volume_gain=request.volume_gain,
    )

    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(request.session_id)
    try:
        agg = await repo.load(agg_id)
    except Exception:
        agg = SoundscapeAggregate(agg_id)

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
    )
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    for ev in events:
        await publish_soundscape_event(ev)

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
    engine = get_or_create_leitmotif_engine(session_id)
    playback = engine.get_active_status()
    return {
        "session_id": session_id,
        "is_playing": playback is not None,
        "active_leitmotif": playback.model_dump() if playback else None,
        "is_ducked": engine.is_ducked,
    }
