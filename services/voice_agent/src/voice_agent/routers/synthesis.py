"""Voice Agent Speech Synthesis and Transcription Router."""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends
from voice_agent.auth import VoicePrincipal, get_voice_principal
from voice_agent.authz import require_speaker
from voice_agent.dependencies import (
    _dispatch_voice_audio_conditioned,
    dsp_pipeline,
)
from voice_agent.dsp import apply_audio_filters
from voice_agent.models import (
    AVAILABLE_PERSONAS,
    TTSRequest,
    TTSResponse,
    VoicePersona,
)
from voice_agent.synthesis_engine import get_speech_synthesizer
from voice_agent.synthesizer import AudioClip
from voice_agent.wav import encode_wav

logger = logging.getLogger("runefoble.voice_agent.synthesis")
router = APIRouter(
    dependencies=[Depends(get_voice_principal)], tags=["Speech Synthesis & Transcription"]
)

DEFAULT_TTS_VOICE = "en-us"


@router.get("/api/v1/voice/personas", response_model=list[VoicePersona])
async def list_personas():
    """List available voice personas for DM and player stand-ins."""
    return list(AVAILABLE_PERSONAS.values())


@router.post("/api/v1/voice/synthesize", response_model=TTSResponse)
@router.post("/api/v1/voice/tts", response_model=TTSResponse)
async def synthesize_voice(req: TTSRequest, principal: VoicePrincipal):
    """Synthesize persona speech, apply DSP filters to that audio, and return the audio it describes."""
    await require_speaker(req.session_id, req.speaker_id, principal.user_id)
    filters = list(req.filters)
    if req.apply_drunk_filter and "drunk" not in filters:
        filters.append("drunk")

    persona = AVAILABLE_PERSONAS.get(req.persona_id)
    pitch = persona.pitch_modifier if persona else 1.0
    voice = persona.tts_voice if persona else DEFAULT_TTS_VOICE

    processed = dsp_pipeline.process(req.text, filters=filters, persona_pitch=pitch)

    # EngineUnavailableError becomes HTTP 503 in the app exception handler. No audio is returned.
    synthesizer = get_speech_synthesizer()
    spoken = await synthesizer.synthesize(req.text, voice=voice)

    filtered_pcm, audio_meta, filter_latency = apply_audio_filters(
        spoken.pcm, filters, sample_rate=spoken.sample_rate
    )
    clip = AudioClip(pcm=filtered_pcm, sample_rate=spoken.sample_rate)
    wav_bytes = encode_wav(clip)
    audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

    effects = list(filters)
    if "drunk" in filters:
        effects.extend(["slur_articulation", "pitch_wobble"])

    dsp_params: dict[str, Any] = processed.dsp_config.model_dump()
    dsp_params.update(audio_meta)
    total_latency = round(filter_latency + processed.latency_ms, 2)

    await _dispatch_voice_audio_conditioned(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        filters_applied=filters,
        latency_ms=total_latency,
        audio_bytes_length=len(filtered_pcm),
    )

    return TTSResponse(
        duration_ms=clip.duration_ms,
        sample_rate_hz=clip.sample_rate,
        content_sha256=hashlib.sha256(wav_bytes).hexdigest(),
        engine=synthesizer.engine_name,
        persona_used=req.persona_id,
        original_text=req.text,
        conditioned_text=processed.conditioned_text,
        effects_applied=sorted(set(effects)),
        dsp_parameters=dsp_params,
        dsp_metadata=dsp_params,
        audio_payload=audio_b64,
        audio_base64=audio_b64,
        latency_ms=total_latency,
    )
