"""Speech and intent routes proxied to The Watcher (TASK-0596).

The gateway verifies the bearer token and forwards the JSON body and the same token to
`the_watcher`. The owner parses the intent, checks `session.participate`, and validates the
body. The gateway adds no check and reads no identity field from the body (ADR-0002).

The speak-and-act route is `watcher_speech_proxy.py` (TASK-0583). Each route is a row in
`ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

SERVICE = "the_watcher"

router = APIRouter(tags=["The Watcher"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/watcher/transcribe-and-act",
        ("api", "v1", "watcher", "transcribe-and-act"),
        SERVICE,
        name="watcher_transcribe_and_act",
        doc="Parse a spoken transcript and dispatch its board action (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/intent/parse",
        ("api", "v1", "watcher", "intent", "parse"),
        SERVICE,
        name="watcher_intent_parse",
        doc="Split a voice command into actions and detect ambiguous targets (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/intent/resolve",
        ("api", "v1", "watcher", "intent", "resolve"),
        SERVICE,
        name="watcher_intent_resolve",
        doc="Resolve a player's answer to a disambiguation prompt (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/intent/execute",
        ("api", "v1", "watcher", "intent", "execute"),
        SERVICE,
        name="watcher_intent_execute",
        doc="Execute a compound action graph with rollback coordination (The Watcher).",
        body="json",
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)
