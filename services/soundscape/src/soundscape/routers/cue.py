"""Tactical sound foley and acoustic cue trigger router (TASK-0050)."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
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
from soundscape.models import SoundscapeCueRequest, SoundscapeCueResponse

router = APIRouter(prefix="/api/v1/soundscape", tags=["Foley & Cues"])


@router.post(
    "/cue",
    response_model=SoundscapeCueResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger a tactical sound effect or foley cue",
)
async def trigger_sound_cue(
    request: SoundscapeCueRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> SoundscapeCueResponse:
    """Trigger a tactical foley cue or sound effect (e.g. fireball, sword slash).

    Zanzibar authorized: caller must have play or run_session permissions.
    """
    can_trigger = await check_user_can_control_soundscape(
        user_id=user_id,
        session_id=request.session_id,
        campaign_id=request.campaign_id,
        spicedb=spicedb,
    )
    if not can_trigger:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient Zanzibar permissions to trigger sound cues",
        )

    mixer = get_or_create_mixer(request.session_id)
    resolved = mixer.resolve_foley_cue(
        cue_name=request.cue_name,
        sound_url=request.sound_url,
        cue_type=request.cue_type,
        volume_gain=request.volume_gain,
        duck_music=request.duck_music,
    )

    cue_id = f"cue-{uuid4().hex[:8]}"

    # Event sourcing aggregate
    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(request.session_id)
    try:
        agg = await repo.load(agg_id)
    except Exception:
        agg = SoundscapeAggregate(agg_id)

    agg.record_cue(
        session_id=request.session_id,
        cue_id=cue_id,
        sound_url=resolved["sound_url"],
        cue_type=resolved["cue_type"],
        volume_gain=resolved["volume_gain"],
        duck_music=resolved["duck_music"],
    )

    if resolved["duck_music"]:
        mixer.set_ducking(True, reason="cue")
        agg.record_ducking_toggle(
            session_id=request.session_id,
            is_ducked=True,
            attenuation_db=-12.0,
            reason="cue",
        )

    events = list(agg.uncommitted_events)
    await repo.save(agg)
    for event in events:
        await publish_soundscape_event(event)

    return SoundscapeCueResponse(
        cue_id=cue_id,
        session_id=request.session_id,
        status="triggered",
        cue_name=resolved["cue_name"],
        sound_url=resolved["sound_url"],
        cue_type=resolved["cue_type"],
        volume_gain=resolved["volume_gain"],
        duck_music=resolved["duck_music"],
    )
