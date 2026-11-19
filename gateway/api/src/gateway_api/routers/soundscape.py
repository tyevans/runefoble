"""Soundscape gateway routes. Each route forwards to the soundscape service (TASK-0589, TASK-0775).

The gateway verifies the bearer token, then forwards the request with that same token. The
soundscape service validates each body and checks every permission (SpiceDB Zanzibar, ADR-0001).
The gateway keeps no soundscape state and runs no soundscape code in process. Each route is a row
in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

SOUNDSCAPE_SERVICE = "soundscape"

router = APIRouter(tags=["Soundscape"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/soundscape/cue",
        ("api", "v1", "soundscape", "cue"),
        SOUNDSCAPE_SERVICE,
        name="trigger_cue",
        doc="Trigger a foley cue. The service checks `play` on the session or campaign.",
        reply="bytes",
        body="raw",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/soundscape/tension",
        ("api", "v1", "soundscape", "tension"),
        SOUNDSCAPE_SERVICE,
        name="get_tension",
        doc="Read the encounter tension of a session. The query string reaches the owner unchanged.",
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/soundscape/tension/calculate",
        ("api", "v1", "soundscape", "tension", "calculate"),
        SOUNDSCAPE_SERVICE,
        name="calculate_encounter_tension",
        doc="Calculate encounter tension and adapt the stems. The service checks session control.",
        reply="bytes",
        body="raw",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/soundscape/stems/override",
        ("api", "v1", "soundscape", "stems", "override"),
        SOUNDSCAPE_SERVICE,
        name="override_soundscape_mood",
        doc="Force a stem profile. The service checks `run_session` or `manage`.",
        reply="bytes",
        body="raw",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/soundscape/duck",
        ("api", "v1", "soundscape", "duck"),
        SOUNDSCAPE_SERVICE,
        name="toggle_ducking",
        doc="Engage or release WebAudio ducking. The service checks session control.",
        reply="bytes",
        body="raw",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/soundscape/leitmotif/{character_id}",
        ("api", "v1", "soundscape", "leitmotif", "profile", "{character_id}"),
        SOUNDSCAPE_SERVICE,
        name="get_leitmotif_profile",
        doc="Read a character leitmotif profile. The service owns the route under `/leitmotif/profile`.",
        query_all=True,
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)
