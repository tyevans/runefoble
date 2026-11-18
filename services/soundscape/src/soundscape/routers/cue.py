"""Tactical sound foley and acoustic cue trigger router (TASK-0050)."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient

from soundscape.dependencies import (
    CallerId,
    check_user_can_trigger_cue,
    get_principal,
)
from soundscape.mixer import AudioStemMixer
from soundscape.models import SoundscapeCueRequest, SoundscapeCueResponse
from soundscape.session_state import load_session_aggregate, save_session_aggregate

router = APIRouter(
    prefix="/api/v1/soundscape", tags=["Foley & Cues"], dependencies=[Depends(get_principal)]
)

# A cue that ducks the music holds the duck for the browser's cue window (2000 ms).
CUE_DUCK_MS = 2000


@router.post(
    "/cue",
    response_model=SoundscapeCueResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger a tactical sound effect or foley cue",
)
async def trigger_sound_cue(
    request: SoundscapeCueRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> SoundscapeCueResponse:
    """Trigger a tactical foley cue or sound effect (e.g. fireball, sword slash).

    Zanzibar authorized: caller needs session participate or control (or campaign play or
    run_session when the request names a campaign).
    """
    can_trigger = await check_user_can_trigger_cue(
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

    resolved = AudioStemMixer().resolve_foley_cue(
        cue_name=request.cue_name,
        sound_url=request.sound_url,
        cue_type=request.cue_type,
        volume_gain=request.volume_gain,
        duck_music=request.duck_music,
    )
    cue_id = f"cue-{uuid4().hex[:8]}"

    agg = await load_session_aggregate(request.session_id)
    agg.record_cue(
        session_id=request.session_id,
        cue_id=cue_id,
        sound_url=resolved["sound_url"],
        cue_type=resolved["cue_type"],
        volume_gain=resolved["volume_gain"],
        duck_music=resolved["duck_music"],
    )
    if resolved["duck_music"]:
        agg.record_ducking_engaged(
            session_id=request.session_id,
            reason="cue",
            duration_ms=CUE_DUCK_MS,
        )
    await save_session_aggregate(agg)

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
