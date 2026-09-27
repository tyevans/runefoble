"""Frontdoor Audio Diagnostic API for neural speech barge-in evaluation."""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field
from runefoble_events.voice_barge_in import (
    NeuralSpeechBargeInDetectedEvent,
    TTSStreamAttenuatedEvent,
)
from voice_agent.dependencies import STREAM_SESSION, STREAM_VOICE, get_event_bus
from voice_agent.dsp.barge_in_filter import BargeInOnsetFilter
from voice_agent.dsp.cosine_crossfade import CosineCrossfadeAttenuator

logger = logging.getLogger("runefoble.voice_agent.audio_filters")
router = APIRouter(tags=["Audio DSP Filters"])


class BargeInEvaluationRequest(BaseModel):
    session_id: str = "sess-diag-1"
    speaker_id: str = "spk-marcus"
    speaker_name: str = "Marcus"
    audio_base64: str | None = None
    outgoing_tts_base64: str | None = None
    sample_rate: int = 16000
    fade_duration_ms: float = 20.0
    energy_threshold: float = 350.0


class BargeInEvaluationResponse(BaseModel):
    session_id: str
    speaker_id: str
    barge_in_detected: bool
    onset_latency_ms: float = 0.0
    confidence: float = 0.0
    rms_energy: float = 0.0
    attenuation_applied: bool = False
    fade_duration_ms: float = 20.0
    attenuated_audio_base64: str | None = None
    peak_tail_amplitude: int = 0
    halt_latency_ms: float = 0.0
    status: str = "success"
    diagnostics: dict[str, float | int | bool] = Field(default_factory=dict)


@router.post("/voice/filters/barge-in/evaluate", response_model=BargeInEvaluationResponse)
@router.post("/api/v1/voice/filters/barge-in/evaluate", response_model=BargeInEvaluationResponse)
async def evaluate_barge_in(req: BargeInEvaluationRequest) -> BargeInEvaluationResponse:
    """Evaluate synthetic audio frames for speech onset and measure halt latency."""
    in_pcm = base64.b64decode(req.audio_base64) if req.audio_base64 else b""
    onset_filter = BargeInOnsetFilter(req.sample_rate, energy_threshold=req.energy_threshold)
    result = onset_filter.evaluate_stream(in_pcm)

    if not result.is_barge_in:
        return BargeInEvaluationResponse(
            session_id=req.session_id,
            speaker_id=req.speaker_id,
            barge_in_detected=False,
            onset_latency_ms=result.onset_latency_ms,
            confidence=result.confidence,
            rms_energy=result.rms_energy,
            fade_duration_ms=req.fade_duration_ms,
        )

    tts_pcm = (
        base64.b64decode(req.outgoing_tts_base64) if req.outgoing_tts_base64 else (in_pcm or b"")
    )
    attenuator = CosineCrossfadeAttenuator(req.fade_duration_ms, req.sample_rate)
    atten_res = attenuator.attenuate(tts_pcm)
    atten_b64 = base64.b64encode(atten_res.faded_audio).decode("ascii")
    halt_lat = round(result.onset_latency_ms + req.fade_duration_ms, 2)

    b_ev = NeuralSpeechBargeInDetectedEvent(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        onset_latency_ms=result.onset_latency_ms,
        confidence=result.confidence,
        rms_energy=result.rms_energy,
    )
    a_ev = TTSStreamAttenuatedEvent(
        session_id=req.session_id,
        stream_id="tts_stream",
        fade_duration_ms=req.fade_duration_ms,
        attenuated_samples_count=atten_res.attenuated_samples_count,
        peak_tail_amplitude=atten_res.peak_tail_amplitude,
        cutoff_position_ms=result.onset_latency_ms,
    )

    bus = get_event_bus()
    for stream in (STREAM_VOICE, STREAM_SESSION):
        for ev in (b_ev, a_ev):
            try:
                await bus.publish_event(stream, ev)
            except Exception as e:
                logger.warning("Failed to publish barge-in CloudEvent: %s", e)

    return BargeInEvaluationResponse(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        barge_in_detected=True,
        onset_latency_ms=result.onset_latency_ms,
        confidence=result.confidence,
        rms_energy=result.rms_energy,
        attenuation_applied=True,
        fade_duration_ms=req.fade_duration_ms,
        attenuated_audio_base64=atten_b64,
        peak_tail_amplitude=atten_res.peak_tail_amplitude,
        halt_latency_ms=halt_lat,
        diagnostics={
            "max_discontinuity": atten_res.max_discontinuity,
            "attenuated_samples_count": atten_res.attenuated_samples_count,
            "speech_frames_count": result.speech_frames_count,
        },
    )


__all__ = ["BargeInEvaluationRequest", "BargeInEvaluationResponse", "router"]
