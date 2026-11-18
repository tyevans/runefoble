"""Voice Agent Microservice.

Handles audio streaming, Speech-To-Text transcription pipelines,
Text-To-Speech synthesis with persona voice models, and dynamic DSP audio conditioning.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.engine_ports import EngineUnavailableError, engine_unavailable_handler
from runefoble_platform.event_publish import event_publish_failures, install_publish_failure_handler
from runefoble_platform.event_sourcing import get_event_store
from runefoble_platform.ui_manifest import load_ui_manifest
from voice_agent.companion_routes import router as companion_router
from voice_agent.companion_socket_routes import router as companion_socket_router
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
    set_watcher_client as _dep_set_watcher_client,
)
from voice_agent.event_bus import event_bus_provider, get_event_bus, set_event_bus
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
from voice_agent.readiness import speech_readiness_problems
from voice_agent.routers import (
    aec_diagnostics_router,
    audio_filters_router,
    audio_router,
    dsp_condition_router,
    duplex_router,
    room_router,
    stream_diagnostics_router,
    stream_router,
    synthesis_router,
    transcribe_router,
    vocal_effects_router,
)
from voice_agent.stt import get_streaming_pipeline
from voice_agent.synthesis_engine import get_speech_synthesizer

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST = load_ui_manifest(
    Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Build the configured speech engines and connect Redis at start-up. A bad engine setting stops the service."""
    get_streaming_pipeline()
    get_speech_synthesizer()
    async with event_bus_provider.lifespan(_app):
        yield


# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

app = FastAPI(
    title="Runefoble - Voice Agent Service",
    version="0.1.0",
    description="Real-time Voice Streaming, STT / TTS Pipelines, and Persona Voice Synthesis.",
    lifespan=lifespan,
)
app.add_exception_handler(EngineUnavailableError, engine_unavailable_handler)
install_authz_error_handlers(app)
register_store_unavailable_handlers(app)
install_publish_failure_handler(app)
app.include_router(room_router)
app.include_router(stream_router)
app.include_router(audio_router)
app.include_router(synthesis_router)
app.include_router(transcribe_router)
app.include_router(duplex_router)
app.include_router(vocal_effects_router)
app.include_router(dsp_condition_router)
app.include_router(stream_diagnostics_router)
app.include_router(companion_router)
app.include_router(companion_socket_router)
app.include_router(audio_filters_router)
app.include_router(aec_diagnostics_router)


def set_watcher_client(client: httpx.AsyncClient | None) -> None:
    _dep_set_watcher_client(client)


@app.get("/healthz")
async def health_check():
    transcriber = get_streaming_pipeline().transcriber
    synthesizer = get_speech_synthesizer()
    problems = await speech_readiness_problems(transcriber, synthesizer)
    body = {
        "status": "not_ready" if problems else "ok",
        "service": "voice_agent",
        "stt_engine": transcriber.engine_name,
        "tts_engine": synthesizer.engine_name,
        "event_publish_failures": event_publish_failures(),
    }
    if problems:
        body["problems"] = problems
        return JSONResponse(body, status_code=503)
    return body


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for voice agent."""
    return UI_MANIFEST


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
    "app",
    "dsp_pipeline",
    "get_event_bus",
    "platform_settings",
    "set_event_bus",
    "set_watcher_client",
    "to_uuid",
]
