"""Frontdoor Audio Diagnostic API for AEC and ERLE validation (TASK-0169)."""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field
from runefoble_events.aec import AECBenchmarkCompletedEvent, EchoSuppressionEngagedEvent
from voice_agent.aec.pipeline import AECPipeline
from voice_agent.dependencies import publish_voice_event

logger = logging.getLogger("runefoble.voice_agent.aec_diagnostics")
router = APIRouter(tags=["Acoustic Echo Cancellation"])


class AECBenchmarkRequest(BaseModel):
    session_id: str = "sess-aec-1"
    speaker_id: str = "spk-player"
    reference_audio_base64: str | None = None
    speaker_audio_base64: str | None = None
    microphone_audio_base64: str | None = None
    mic_audio_base64: str | None = None
    sample_rate: int = 16000
    filter_length: int = 512
    step_size: float = 0.25
    erle_target_db: float = 35.0


class AECBenchmarkResponse(BaseModel):
    session_id: str
    speaker_id: str
    erle_db: float
    erle_target_db: float = 35.0
    passed: bool
    double_talk_detected: bool = False
    echo_detected: bool = False
    attenuation_applied: bool = True
    cleaned_audio_base64: str
    initial_rms: float
    residual_rms: float
    status: str = "success"
    diagnostics: dict[str, float | int | bool | str] = Field(default_factory=dict)


@router.post("/voice/aec/benchmark", response_model=AECBenchmarkResponse)
@router.post("/api/v1/voice/aec/benchmark", response_model=AECBenchmarkResponse)
async def run_aec_benchmark(req: AECBenchmarkRequest) -> AECBenchmarkResponse:
    """Benchmark paired loudspeaker and microphone PCM streams to validate ERLE > 35dB."""
    ref_b64 = req.reference_audio_base64 or req.speaker_audio_base64 or ""
    mic_b64 = req.microphone_audio_base64 or req.mic_audio_base64 or ""

    ref_pcm = base64.b64decode(ref_b64) if ref_b64 else b""
    mic_pcm = base64.b64decode(mic_b64) if mic_b64 else b""

    pipeline = AECPipeline(
        sample_rate=req.sample_rate,
        filter_length=req.filter_length,
        step_size=req.step_size,
    )
    res = pipeline.benchmark(ref_pcm, mic_pcm, target_erle_db=req.erle_target_db)

    b_ev = AECBenchmarkCompletedEvent(
        session_id=req.session_id,
        erle_db=res["erle_db"],
        target_erle_db=req.erle_target_db,
        passed=res["passed"],
        double_talk_detected=res["double_talk_detected"],
        filter_length=req.filter_length,
    )
    await publish_voice_event(b_ev)

    if res["echo_detected"]:
        e_ev = EchoSuppressionEngagedEvent(
            session_id=req.session_id,
            speaker_id=req.speaker_id,
            erle_db=res["erle_db"],
            attenuation_db=res["erle_db"],
            is_double_talk=res["double_talk_detected"],
        )
        await publish_voice_event(e_ev)

    clean_b64 = base64.b64encode(res["cleaned_pcm"]).decode("ascii")
    return AECBenchmarkResponse(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        erle_db=res["erle_db"],
        erle_target_db=req.erle_target_db,
        passed=res["passed"],
        double_talk_detected=res["double_talk_detected"],
        echo_detected=res["echo_detected"],
        attenuation_applied=res["echo_detected"],
        cleaned_audio_base64=clean_b64,
        initial_rms=res["initial_rms"],
        residual_rms=res["residual_rms"],
        diagnostics={
            "filter_length": req.filter_length,
            "step_size": req.step_size,
            "sample_rate": req.sample_rate,
        },
    )


__all__ = ["AECBenchmarkRequest", "AECBenchmarkResponse", "router"]
