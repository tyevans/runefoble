"""Voice Agent Microservice.

Handles audio streaming, Speech-To-Text transcription pipelines,
and Text-To-Speech synthesis with persona voice models (DM, heroic fighter, dwarven cleric).
"""

import logging
import os
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field
from runefoble_events.events import PlayerSpokeEvent
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus

logger = logging.getLogger("runefoble.voice_agent")
WATCHER_URL = os.environ.get("RUNEFOBLE_WATCHER_URL", "http://localhost:8001")
STREAM_SESSION = "runefoble.events.session"

app = FastAPI(
    title="Runefoble - Voice Agent Service",
    version="0.1.0",
    description="Real-time Voice Streaming, STT / TTS Pipelines, and Persona Voice Synthesis.",
)

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


class TTSRequest(BaseModel):
    text: str
    persona_id: str = "watcher_dm"
    apply_drunk_filter: bool = False


class TTSResponse(BaseModel):
    audio_stream_url: str
    duration_ms: int
    persona_used: str
    effects_applied: list[str] = Field(default_factory=list)


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


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "voice_agent"}


@app.get("/api/v1/voice/personas", response_model=list[VoicePersona])
async def list_personas():
    return list(AVAILABLE_PERSONAS.values())


@app.post("/api/v1/voice/synthesize", response_model=TTSResponse)
async def synthesize_voice(req: TTSRequest):
    """Synthesize speech audio stream for DM narration or AI stand-in dialogue."""
    effects = []
    if req.apply_drunk_filter:
        effects.append("slur_articulation")
        effects.append("pitch_wobble")

    return TTSResponse(
        audio_stream_url=f"/streams/audio/{req.persona_id}_{abs(hash(req.text)) % 10000}.wav",
        duration_ms=max(1200, len(req.text) * 65),
        persona_used=req.persona_id,
        effects_applied=effects,
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


def main():
    import uvicorn

    uvicorn.run("voice_agent.main:app", host="0.0.0.0", port=8005, reload=True)


if __name__ == "__main__":
    main()
