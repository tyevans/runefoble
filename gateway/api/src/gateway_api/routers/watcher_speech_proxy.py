"""Speak-and-act proxied to The Watcher speech intent route (TASK-0583).

The gateway verifies the caller's bearer token, then forwards the raw JSON body and the same
token to `the_watcher`. The Watcher owns intent parsing and checks `session.participate` and
the speaker (ADR-0002, ADR-0015). The gateway parses no speech and changes no board state.
A 4xx from The Watcher (for example a missing transcript, or a refused caller) passes through
unchanged. An unreachable Watcher returns 503.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from gateway_api.auth import CallerPrincipal
from gateway_api.proxy import forward_bytes

SERVICE = "the_watcher"
INTENT_PATH = "/api/v1/watcher/intent"

# The Watcher calls the inference worker (2.0 s) and board_state for visible tokens (2.0 s).
# The gateway waits longer than the owner's worst case, so the owner answers first.
SPEAK_AND_ACT_TIMEOUT_S = 5.0

router = APIRouter(tags=["Tabletop & Game Sessions"])


@router.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(request: Request, user: CallerPrincipal) -> Response:
    """Parse one spoken transcript into an intent (The Watcher). The body goes to the owner as sent."""
    return await forward_bytes(
        request,
        service=SERVICE,
        method="POST",
        path=INTENT_PATH,
        timeout=SPEAK_AND_ACT_TIMEOUT_S,
    )
