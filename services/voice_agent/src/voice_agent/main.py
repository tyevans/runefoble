"""Voice Agent Microservice.

Handles audio streaming, Speech-To-Text transcription pipelines,
Text-To-Speech synthesis with persona voice models, and dynamic DSP audio conditioning.
"""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.dependencies import (
    STREAM_SESSION,
    STREAM_VOICE,
    WATCHER_URL,
    _dispatch_voice_audio_conditioned,
    dsp_pipeline,
    platform_settings,
    to_uuid,
)
from voice_agent.dependencies import (
    get_event_bus as _dep_get_event_bus,
)
from voice_agent.dependencies import (
    set_event_bus as _dep_set_event_bus,
)
from voice_agent.dependencies import (
    set_watcher_client as _dep_set_watcher_client,
)
from voice_agent.models import (
    AVAILABLE_PERSONAS,
    DSPApplyRequest,
    DSPApplyResponse,
    TranscribeRequest,
    TranscribeResponse,
    TTSRequest,
    TTSResponse,
    VoicePersona,
)
from voice_agent.routers import (
    audio_filters_router,
    audio_router,
    duplex_router,
    room_router,
    stream_diagnostics_router,
    stream_router,
    synthesis_router,
    vocal_effects_router,
)

app = FastAPI(
    title="Runefoble - Voice Agent Service",
    version="0.1.0",
    description="Real-time Voice Streaming, STT / TTS Pipelines, and Persona Voice Synthesis.",
)
app.include_router(room_router)
app.include_router(stream_router)
app.include_router(audio_router)
app.include_router(synthesis_router)
app.include_router(duplex_router)
app.include_router(vocal_effects_router)
app.include_router(stream_diagnostics_router)
app.include_router(audio_filters_router)

_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = _dep_get_event_bus()
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus
    _dep_set_event_bus(bus)


def set_watcher_client(client: httpx.AsyncClient | None) -> None:
    _dep_set_watcher_client(client)


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "voice_agent"}


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for voice agent."""
    return {
        "service": "voice_agent",
        "package": "@runefoble/voice-agent-ui",
        "components": [
            "runefoble-voice-controls",
            "runefoble-audio-indicator",
            "runefoble-mobile-companion",
            "runefoble-voice-duplex-controls",
            "audio-stream-controller",
            "haptic-ping-panel",
            "connection-status-badge",
            "runefoble-vocal-modulator",
            "runefoble-vocal-sliders",
        ],
        "tags": [
            "runefoble-voice-controls",
            "runefoble-audio-indicator",
            "runefoble-mobile-companion",
            "runefoble-voice-duplex-controls",
            "audio-stream-controller",
            "haptic-ping-panel",
            "connection-status-badge",
            "runefoble-vocal-modulator",
            "runefoble-vocal-sliders",
        ],
        "styles": [
            "./src/runefoble-voice-controls.styles.ts",
            "./src/runefoble-mobile-companion.styles.ts",
            "./src/duplex/styles/index.ts",
            "./src/mobile_companion/styles/index.ts",
            "./src/runefoble-vocal-modulator.styles.ts",
        ],
        "scripts": ["./src/index.ts"],
        "version": "0.1.0",
    }


def main():
    import uvicorn

    uvicorn.run("voice_agent.main:app", host="0.0.0.0", port=8005, reload=True)


if __name__ == "__main__":
    main()


__all__ = [
    "AVAILABLE_PERSONAS",
    "DSPApplyRequest",
    "DSPApplyResponse",
    "STREAM_SESSION",
    "STREAM_VOICE",
    "TTSRequest",
    "TTSResponse",
    "TranscribeRequest",
    "TranscribeResponse",
    "VoicePersona",
    "WATCHER_URL",
    "_dispatch_voice_audio_conditioned",
    "_event_bus",
    "app",
    "dsp_pipeline",
    "get_event_bus",
    "platform_settings",
    "set_event_bus",
    "set_watcher_client",
    "to_uuid",
]
