"""Voice Agent Audio DSP Conditioning Router."""

from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException
from voice_agent.auth import CallerPrincipal, get_principal
from voice_agent.authz import require_speaker
from voice_agent.filters import apply_audio_filters
from voice_agent.models import DSPApplyRequest, DSPApplyResponse

router = APIRouter(dependencies=[Depends(get_principal)], tags=["Audio DSP"])


@router.post("/api/v1/voice/dsp/apply", response_model=DSPApplyResponse)
async def apply_dsp(req: DSPApplyRequest, principal: CallerPrincipal):
    """Apply dynamic DSP filters to supplied audio. The route never synthesises a carrier."""
    await require_speaker(req.session_id, req.speaker_id, principal.user_id)
    filters = list(req.filters)

    if not req.audio_base64:
        raise HTTPException(status_code=422, detail="audio_base64 is required")
    try:
        input_bytes = base64.b64decode(req.audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"audio_base64 is not base64: {exc}") from exc
    try:
        out_bytes, meta, latency_ms = apply_audio_filters(
            input_bytes, filters=filters, sample_rate=req.sample_rate
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audio_b64 = base64.b64encode(out_bytes).decode("ascii")

    return DSPApplyResponse(
        audio_base64=audio_b64,
        audio_bytes_length=len(out_bytes),
        filters_applied=filters,
        latency_ms=round(latency_ms, 2),
        dsp_parameters=meta,
    )
