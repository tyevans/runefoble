"""Gateway proxy for voice room and stream diagnostics routes owned by voice_agent (TASK-0593).

Each route forwards the caller's bearer token to voice_agent. voice_agent verifies the token
and checks the session permission itself (ADR-0015 c, Hard Invariant 1). The gateway keeps
no room state and adds no permission check of its own. Paths match the owner's public paths.
Each route is a row in `ROUTES` (TASK-0822).
The transcribe route carries Push to Talk audio (TASK-0946). The bare `/voice/streams` paths are gone (TASK-0494).

"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

router = APIRouter(tags=["Voice Rooms"])

VOICE_SERVICE = "voice_agent"

# Budget rule (TASK-0946): the transcribe route runs speech-to-text, then forwards the transcript
# to The Watcher (intent 2 s, board read 2 s, proposal 2 s; sum 6 s). Speech-to-text of one
# utterance takes up to a few seconds more. The gateway waits 10 s, longer than the owner's
# worst case, so the owner answers first.
TRANSCRIBE_TIMEOUT_S = 10.0

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/voice/transcribe",
        ("api", "v1", "voice", "transcribe"),
        VOICE_SERVICE,
        name="transcribe_speech",
        doc=(
            "Forward one Push to Talk utterance (WAV, base64) or typed text. voice_agent "
            "transcribes it, checks the speaker, and forwards the transcript to The Watcher."
        ),
        body="json",
        principal=True,
        timeout=TRANSCRIBE_TIMEOUT_S,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/voice/rooms/{session_id}",
        ("api", "v1", "voice", "rooms", "{session_id}"),
        VOICE_SERVICE,
        name="get_voice_room",
        doc="Retrieve room participants, roles, mute states, and audio telemetry from the voice service.",
    ),
    ProxyRoute(
        "POST",
        "/api/v1/voice/rooms/{session_id}/kick",
        ("api", "v1", "voice", "rooms", "{session_id}", "kick"),
        VOICE_SERVICE,
        name="kick_voice_peer",
        doc="Forward a DM kick request. voice_agent checks session.control.",
        body="json",
    ),
    ProxyRoute(
        "GET",
        "/api/v1/voice/streams/{session_id}/quality",
        ("api", "v1", "voice", "streams", "{session_id}", "quality"),
        VOICE_SERVICE,
        name="get_stream_quality",
        doc="Forward a stream quality query. The optional peer_id query parameter is passed on.",
        query_all=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/voice/streams/{session_id}/report",
        ("api", "v1", "voice", "streams", "{session_id}", "report"),
        VOICE_SERVICE,
        name="submit_rtcp_report",
        doc="Forward an RTCP receiver report. voice_agent evaluates it and adapts the codec.",
        body="json",
    ),
    ProxyRoute(
        "GET",
        "/api/v1/mobile/companion/profiles",
        ("api", "v1", "mobile", "companion", "profiles"),
        VOICE_SERVICE,
        name="get_mobile_profiles",
        doc="Forward the companion audio profile list. voice_agent owns the profiles.",
    ),
    ProxyRoute(
        "POST",
        "/api/v1/mobile/companion/{session_id}/whisper",
        ("api", "v1", "mobile", "companion", "{session_id}", "whisper"),
        VOICE_SERVICE,
        name="dispatch_whisper",
        doc="Forward a secret DM whisper. voice_agent checks session.control.",
        body="json",
    ),
    ProxyRoute(
        "POST",
        "/api/v1/mobile/companion/{session_id}/turn-alert",
        ("api", "v1", "mobile", "companion", "{session_id}", "turn-alert"),
        VOICE_SERVICE,
        name="dispatch_turn_alert",
        doc="Forward a combat turn alert. voice_agent checks session.control.",
        body="json",
    ),
)

register_proxy_routes(router, ROUTES)
