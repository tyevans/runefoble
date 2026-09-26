"""Voice Agent Microservice.

Handles audio streaming, Speech-To-Text transcription pipelines,
and Text-To-Speech synthesis with persona voice models (DM, heroic fighter, dwarven cleric).
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="Runefoble - Voice Agent Service",
    version="0.1.0",
    description="Real-time Voice Streaming, STT / TTS Pipelines, and Persona Voice Synthesis.",
)


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


def main():
    import uvicorn

    uvicorn.run("voice_agent.main:app", host="0.0.0.0", port=8005, reload=True)


if __name__ == "__main__":
    main()
