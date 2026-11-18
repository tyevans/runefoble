"""WebSocket routes for the WebRTC signaling room and the mobile companion (TASK-0593).

The gateway relays `/ws/voice/{session_id}` and `/ws/mobile-companion/{session_id}` to these
routes. Each route verifies the bearer and checks `session.observe` itself.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket
from voice_agent.companion_socket import mobile_companion_websocket_endpoint
from voice_agent.signaling.endpoint import voice_signaling_websocket_endpoint

router = APIRouter(tags=["Voice Signaling"])


@router.websocket("/ws/voice/{session_id}")
async def voice_signaling_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebRTC voice room signaling. Needs `session.observe`."""
    await voice_signaling_websocket_endpoint(websocket, session_id)


@router.websocket("/ws/mobile-companion/{session_id}")
async def mobile_companion_websocket(websocket: WebSocket, session_id: str) -> None:
    """Low-bandwidth mobile companion and haptic channel. Needs `session.observe`."""
    await mobile_companion_websocket_endpoint(websocket, session_id)


__all__ = ["router"]
