"""Voice Agent Audio DSP Conditioning Router."""

from __future__ import annotations

import base64

from fastapi import APIRouter
from voice_agent.dependencies import _dispatch_voice_audio_conditioned
from voice_agent.dsp import apply_audio_filters
from voice_agent.models import DSPApplyRequest, DSPApplyResponse

router = APIRouter(tags=["Audio DSP"])


@router.post("/api/v1/voice/dsp/apply", response_model=DSPApplyResponse)
async def apply_dsp(req: DSPApplyRequest):
    """Apply dynamic DSP filters to an audio stream or synthesize conditioned audio."""
    filters = list(req.filters)
    if req.filter and req.filter not in filters:
        filters.append(req.filter)

    input_bytes = None
    if req.audio_base64:
        try:
            input_bytes = base64.b64decode(req.audio_base64)
        except Exception:
            input_bytes = None

    out_bytes, meta, latency_ms = apply_audio_filters(
        input_bytes, filters=filters, sample_rate=req.sample_rate
    )
    audio_b64 = base64.b64encode(out_bytes).decode("ascii")

    await _dispatch_voice_audio_conditioned(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        filters_applied=filters,
        latency_ms=round(latency_ms, 2),
        audio_bytes_length=len(out_bytes),
    )

    return DSPApplyResponse(
        audio_base64=audio_b64,
        audio_payload=audio_b64,
        audio_bytes_length=len(out_bytes),
        audio_stream_url=f"/streams/dsp/{abs(hash(audio_b64)) % 10000}.wav",
        filters_applied=filters,
        latency_ms=round(latency_ms, 2),
        dsp_metadata=meta,
        dsp_parameters=meta,
    )
