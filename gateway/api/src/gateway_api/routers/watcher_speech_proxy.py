"""Speak-and-act proxied to The Watcher speech intent route (TASK-0583).

The gateway verifies the caller's bearer token, then forwards the raw JSON body and the same
token to `the_watcher`. The Watcher owns intent parsing and checks `session.participate` and
the speaker (ADR-0002, ADR-0015). The gateway parses no speech and changes no board state.
A 4xx from The Watcher (for example a missing transcript, or a refused caller) passes through
unchanged. An unreachable Watcher returns 503.
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

SERVICE = "the_watcher"

# Budget rule (TASK-0948): this timeout must be greater than the sum of The Watcher's intent
# budget, board read budget and proposal budget (RUNEFOBLE_WATCHER_INTENT_TIMEOUT_S,
# RUNEFOBLE_WATCHER_BOARD_TIMEOUT_S, RUNEFOBLE_WATCHER_PROPOSAL_TIMEOUT_S; defaults 2 s each,
# sum 6 s). The gateway waits longer than the owner's worst case, so the owner answers first.
SPEAK_AND_ACT_TIMEOUT_S = 8.0

router = APIRouter(tags=["Tabletop & Game Sessions"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/watcher/speak-and-act",
        ("api", "v1", "watcher", "transcribe-and-act"),
        SERVICE,
        name="speak_and_act",
        doc=(
            "Parse one spoken transcript into an intent (The Watcher). "
            "The body goes to the owner as sent."
        ),
        reply="bytes",
        body="raw",
        returns="response",
        principal=True,
        timeout=SPEAK_AND_ACT_TIMEOUT_S,
    ),
)

register_proxy_routes(router, ROUTES)
