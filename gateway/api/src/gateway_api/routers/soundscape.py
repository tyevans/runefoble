"""Soundscape gateway routes. Each route forwards to the soundscape service (TASK-0589, TASK-0775).

The gateway verifies the bearer token, then forwards the request with that same token. The
soundscape service validates each body and checks every permission (SpiceDB Zanzibar, ADR-0001).
The gateway keeps no soundscape state and runs no soundscape code in process.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from gateway_api.auth import CallerPrincipal
from gateway_api.proxy import forward_bytes, forward_json
from runefoble_platform.service_client import path

SOUNDSCAPE_SERVICE = "soundscape"

router = APIRouter(prefix="/api/v1/soundscape", tags=["Soundscape"])


@router.post("/cue")
async def trigger_cue(user: CallerPrincipal, request: Request) -> Any:
    """Trigger a foley cue. The service checks `play` on the session or campaign."""
    return await forward_bytes(
        request,
        service=SOUNDSCAPE_SERVICE,
        method="POST",
        path=path("api", "v1", "soundscape", "cue"),
    )


@router.get("/tension")
async def get_tension(user: CallerPrincipal, request: Request) -> Any:
    """Read the encounter tension of a session. The query string reaches the owner unchanged."""
    return await forward_json(
        request,
        service=SOUNDSCAPE_SERVICE,
        method="GET",
        path=path("api", "v1", "soundscape", "tension"),
        params=dict(request.query_params),
    )


@router.post("/tension/calculate")
async def calculate_encounter_tension(user: CallerPrincipal, request: Request) -> Any:
    """Calculate encounter tension and adapt the stems. The service checks session control."""
    return await forward_bytes(
        request,
        service=SOUNDSCAPE_SERVICE,
        method="POST",
        path=path("api", "v1", "soundscape", "tension", "calculate"),
    )


@router.post("/stems/override")
async def override_soundscape_mood(user: CallerPrincipal, request: Request) -> Any:
    """Force a stem profile. The service checks `run_session` or `manage`."""
    return await forward_bytes(
        request,
        service=SOUNDSCAPE_SERVICE,
        method="POST",
        path=path("api", "v1", "soundscape", "stems", "override"),
    )


@router.post("/duck")
async def toggle_ducking(user: CallerPrincipal, request: Request) -> Any:
    """Engage or release WebAudio ducking. The service checks session control."""
    return await forward_bytes(
        request,
        service=SOUNDSCAPE_SERVICE,
        method="POST",
        path=path("api", "v1", "soundscape", "duck"),
    )


@router.get("/leitmotif/{character_id}")
async def get_leitmotif_profile(character_id: str, user: CallerPrincipal, request: Request) -> Any:
    """Read a character leitmotif profile. The service owns the route under `/leitmotif/profile`."""
    return await forward_json(
        request,
        service=SOUNDSCAPE_SERVICE,
        method="GET",
        path=path("api", "v1", "soundscape", "leitmotif", "profile", character_id),
        params=dict(request.query_params),
    )
