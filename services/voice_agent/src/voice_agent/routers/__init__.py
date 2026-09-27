"""Voice Agent APIRouters."""

from __future__ import annotations

from voice_agent.room_routes import router as room_router
from voice_agent.routers.aec_diagnostics import router as aec_diagnostics_router
from voice_agent.routers.audio import router as audio_router
from voice_agent.routers.audio_filters import router as audio_filters_router
from voice_agent.routers.duplex import router as duplex_router
from voice_agent.routers.stream_diagnostics import router as stream_diagnostics_router
from voice_agent.routers.synthesis import router as synthesis_router
from voice_agent.routers.vocal_effects import router as vocal_effects_router
from voice_agent.stream_routes import router as stream_router

__all__ = [
    "aec_diagnostics_router",
    "audio_filters_router",
    "audio_router",
    "duplex_router",
    "room_router",
    "stream_diagnostics_router",
    "stream_router",
    "synthesis_router",
    "vocal_effects_router",
]
