"""Voice Agent Speech Synthesis and Transcription Router."""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

import httpx
from fastapi import APIRouter
from runefoble_events.events import PlayerSpokeEvent
from voice_agent.dependencies import (
    STREAM_SESSION,
    WATCHER_URL,
    _dispatch_voice_audio_conditioned,
    dsp_pipeline,
    get_event_bus,
    to_uuid,
)
from voice_agent.dsp import apply_audio_filters
from voice_agent.models import (
    AVAILABLE_PERSONAS,
    TranscribeRequest,
    TranscribeResponse,
    TTSRequest,
    TTSResponse,
    VoicePersona,
)
from voice_agent.stt import get_streaming_pipeline
from voice_agent.synthesis_engine import get_speech_synthesizer
from voice_agent.synthesizer import AudioClip
from voice_agent.wav import encode_wav

logger = logging.getLogger("runefoble.voice_agent.synthesis")
router = APIRouter(tags=["Speech Synthesis & Transcription"])

DEFAULT_TTS_VOICE = "en-us"


@router.get("/api/v1/voice/personas", response_model=list[VoicePersona])
async def list_personas():
    """List available voice personas for DM and player stand-ins."""
    return list(AVAILABLE_PERSONAS.values())


@router.post("/api/v1/voice/synthesize", response_model=TTSResponse)
@router.post("/api/v1/voice/tts", response_model=TTSResponse)
async def synthesize_voice(req: TTSRequest):
    """Synthesize persona speech, apply DSP filters to that audio, and return the audio it describes."""
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


@router.post("/api/v1/voice/transcribe", response_model=TranscribeResponse)
async def transcribe_speech(req: TranscribeRequest):
    """Transcribe player speech, emit PlayerSpokeEvent, and forward to The Watcher."""
    transcript = req.transcript or "I inspect my surroundings."
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id)

    # 1. Emit PlayerSpokeEvent
    spoke_event = PlayerSpokeEvent(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        transcript=transcript,
        is_whisper=req.is_whisper,
        target_character_id=req.target_character_id,
    )
    bus = get_event_bus()
    event_entry_id = None
    try:
        event_entry_id = await bus.publish_event(STREAM_SESSION, spoke_event)
    except Exception as e:
        logger.warning(
            "Failed to publish PlayerSpokeEvent to Redis stream '%s': %s", STREAM_SESSION, e
        )

    # 2. Forward to The Watcher
    watcher_intent = None
    try:
        watcher_client = get_streaming_pipeline()._watcher_client
        if watcher_client:
            resp = await watcher_client.post(
                "/api/v1/watcher/transcribe-and-act",
                json={
                    "speaker_id": req.speaker_id,
                    "speaker_name": req.speaker_name,
                    "transcript": transcript,
                    "session_id": req.session_id,
                    "campaign_id": req.campaign_id,
                },
            )
            if resp.status_code == 200:
                watcher_intent = resp.json()
        else:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{WATCHER_URL}/api/v1/watcher/transcribe-and-act",
                    json={
                        "speaker_id": req.speaker_id,
                        "speaker_name": req.speaker_name,
                        "transcript": transcript,
                        "session_id": req.session_id,
                        "campaign_id": req.campaign_id,
                    },
                )
                if resp.status_code == 200:
                    watcher_intent = resp.json()
    except Exception as e:
        logger.warning("Failed to forward transcript to The Watcher: %s", e)

    return TranscribeResponse(
        transcript=transcript,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        event_id=event_entry_id,
        watcher_intent=watcher_intent,
    )
