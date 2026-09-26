"""Voice Agent Microservice.

Handles audio streaming, Speech-To-Text transcription pipelines,
Text-To-Speech synthesis with persona voice models, and dynamic DSP audio conditioning.
"""

import base64
import logging
import os
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field
from runefoble_events.events import PlayerSpokeEvent, VoiceAudioConditioned
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.dsp import (
    VoiceDSPPipeline,
    apply_audio_filters,
)
from voice_agent.room import get_voice_room_coordinator
from voice_agent.room_routes import router as room_router
from voice_agent.stream_routes import router as stream_router
from voice_agent.stt import get_streaming_pipeline

logger = logging.getLogger("runefoble.voice_agent")
WATCHER_URL = os.environ.get("RUNEFOBLE_WATCHER_URL", "http://localhost:8001")
STREAM_SESSION = "runefoble.events.session"
STREAM_VOICE = "runefoble.events.voice"

app = FastAPI(
    title="Runefoble - Voice Agent Service",
    version="0.1.0",
    description="Real-time Voice Streaming, STT / TTS Pipelines, and Persona Voice Synthesis.",
)
app.include_router(room_router)
app.include_router(stream_router)

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus
    get_voice_room_coordinator().set_event_bus(bus)
    get_streaming_pipeline().set_event_bus(bus)


def set_watcher_client(client: httpx.AsyncClient | None) -> None:
    get_streaming_pipeline().set_watcher_client(client)


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))


class VoicePersona(BaseModel):
    id: str
    name: str
    description: str
    pitch_modifier: float = 1.0
    speed_modifier: float = 1.0
    accent: str = "neutral"


dsp_pipeline = VoiceDSPPipeline()


class DSPApplyRequest(BaseModel):
    filter: str | None = None
    filters: list[str] = Field(default_factory=list)
    audio_base64: str | None = None
    sample_rate: int = 16000
    session_id: str = "session_default"
    speaker_id: str = "speaker_default"
    speaker_name: str = "Unknown"


class DSPApplyResponse(BaseModel):
    audio_base64: str
    audio_payload: str
    audio_bytes_length: int
    audio_stream_url: str = ""
    filters_applied: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    dsp_metadata: dict[str, Any] = Field(default_factory=dict)
    dsp_parameters: dict[str, Any] = Field(default_factory=dict)


class TTSRequest(BaseModel):
    text: str
    persona_id: str = "watcher_dm"
    apply_drunk_filter: bool = False
    filters: list[str] = Field(default_factory=list)
    session_id: str = "session_default"
    speaker_id: str = "speaker_default"
    speaker_name: str = "The Watcher"


class TTSResponse(BaseModel):
    audio_stream_url: str
    duration_ms: int
    persona_used: str
    original_text: str = ""
    conditioned_text: str = ""
    effects_applied: list[str] = Field(default_factory=list)
    dsp_parameters: dict[str, Any] = Field(default_factory=dict)
    dsp_metadata: dict[str, Any] = Field(default_factory=dict)
    audio_payload: str = ""
    audio_base64: str = ""
    latency_ms: float = 0.0


class TranscribeRequest(BaseModel):
    speaker_id: str
    speaker_name: str
    session_id: str
    campaign_id: str
    transcript: str | None = None
    audio_base64: str | None = None
    is_whisper: bool = False
    target_character_id: str | None = None


class TranscribeResponse(BaseModel):
    transcript: str
    speaker_id: str
    speaker_name: str
    event_id: str | None = None
    watcher_intent: dict[str, Any] | None = None


AVAILABLE_PERSONAS: dict[str, VoicePersona] = {
    "watcher_dm": VoicePersona(
        id="watcher_dm",
        name="The Watcher (Deep Mystical)",
        description="Resonant, deep baritone with subtle cavern reverb for the AI DM.",
        pitch_modifier=0.85,
    ),
    "kyra_stand_in": VoicePersona(
        id="kyra_stand_in",
        name="Kyra Stand-in (Sun Cleric)",
        description="Warm, assertive feminine voice, adaptable with intoxication slurs.",
        pitch_modifier=1.1,
    ),
    "valeros_fighter": VoicePersona(
        id="valeros_fighter",
        name="Valeros (Rugged Fighter)",
        description="Gravelly, confident adventurer cadence.",
        pitch_modifier=0.95,
    ),
}


async def _dispatch_voice_audio_conditioned(
    session_id: str,
    speaker_id: str,
    speaker_name: str,
    filters_applied: list[str],
    latency_ms: float,
    audio_bytes_length: int,
) -> None:
    event = VoiceAudioConditioned(
        session_id=session_id,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        filters_applied=filters_applied,
        latency_ms=latency_ms,
        audio_bytes_length=audio_bytes_length,
    )
    bus = get_event_bus()
    for stream in (STREAM_SESSION, STREAM_VOICE):
        try:
            await bus.publish_event(stream, event)
        except Exception as e:
            logger.warning("Failed to publish VoiceAudioConditioned to '%s': %s", stream, e)


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "voice_agent"}


@app.get("/api/v1/voice/personas", response_model=list[VoicePersona])
async def list_personas():
    return list(AVAILABLE_PERSONAS.values())


@app.post("/api/v1/voice/dsp/apply", response_model=DSPApplyResponse)
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


@app.post("/api/v1/voice/synthesize", response_model=TTSResponse)
@app.post("/api/v1/voice/tts", response_model=TTSResponse)
async def synthesize_voice(req: TTSRequest):
    """Synthesize speech audio stream with DSP audio conditioning and phonetic slurs."""
    filters = list(req.filters)
    if req.apply_drunk_filter and "drunk" not in filters:
        filters.append("drunk")

    persona = AVAILABLE_PERSONAS.get(req.persona_id)
    pitch = persona.pitch_modifier if persona else 1.0

    processed = dsp_pipeline.process(req.text, filters=filters, persona_pitch=pitch)

    raw_audio, audio_meta, filter_latency = apply_audio_filters(None, filters)
    audio_b64 = base64.b64encode(raw_audio).decode("ascii")

    effects = list(filters)
    if "drunk" in filters:
        effects.extend(["slur_articulation", "pitch_wobble"])

    dsp_params = processed.dsp_config.model_dump()
    dsp_params.update(audio_meta)

    total_latency = round(filter_latency + processed.latency_ms, 2)

    await _dispatch_voice_audio_conditioned(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        filters_applied=filters,
        latency_ms=total_latency,
        audio_bytes_length=len(raw_audio),
    )

    return TTSResponse(
        audio_stream_url=f"/streams/audio/{req.persona_id}_{abs(hash(processed.conditioned_text)) % 10000}.wav",
        duration_ms=max(1200, len(processed.conditioned_text) * 65),
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


@app.post("/api/v1/voice/transcribe", response_model=TranscribeResponse)
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


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for voice agent."""
    return {
        "service": "voice_agent",
        "package": "@runefoble/voice-agent-ui",
        "components": ["runefoble-voice-controls", "runefoble-audio-indicator"],
        "version": "0.1.0",
    }


def main():
    import uvicorn

    uvicorn.run("voice_agent.main:app", host="0.0.0.0", port=8005, reload=True)


if __name__ == "__main__":
    main()
