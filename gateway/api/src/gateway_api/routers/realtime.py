"""Gateway WebSocket routes: campaign, session, voice, companion, and minigame sockets.

Each handler admits the socket and then hands it to its owner. The campaign and session
sockets run in the gateway. The voice, companion, and minigame sockets are relayed to their
owning service (ADR-0015 b, c).
"""

from fastapi import APIRouter, WebSocket
from gateway_api.session_websocket import session_websocket_endpoint
from gateway_api.websocket_endpoint import campaign_websocket_endpoint
from gateway_api.websocket_relay import relay_websocket

router = APIRouter()


@router.websocket("/ws/campaigns/{campaign_id}")
async def campaign_websocket(websocket: WebSocket, campaign_id: str) -> None:
    """Zanzibar-protected real-time WebSocket stream for campaign mutations."""
    await campaign_websocket_endpoint(websocket, campaign_id)


@router.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    """Realtime stream connecting board, voice, and Watcher chronicle."""
    await session_websocket_endpoint(websocket, session_id)


@router.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebRTC live voice room signaling. Relayed to voice_agent, which checks session.observe."""
    await relay_websocket(websocket, service="voice_agent", segments=("ws", "voice", session_id))


@router.websocket("/ws/mobile-companion/{session_id}")
async def mobile_companion_websocket(websocket: WebSocket, session_id: str) -> None:
    """Mobile companion and haptic channel. Relayed to voice_agent, which checks session.observe."""
    await relay_websocket(
        websocket, service="voice_agent", segments=("ws", "mobile-companion", session_id)
    )


@router.websocket("/ws/establishments/{establishment_id}/tables/{table_id}")
async def gateway_establishment_table_ws(
    websocket: WebSocket,
    establishment_id: str,
    table_id: str,
) -> None:
    """Establishment-scoped minigame table socket. game_session owns it; the gateway relays frames."""
    await relay_websocket(
        websocket,
        service="game_session",
        segments=("ws", "establishments", establishment_id, "tables", table_id),
    )


@router.websocket("/ws/minigames/{table_id}")
async def gateway_standalone_minigame_ws(
    websocket: WebSocket,
    table_id: str,
) -> None:
    """Standalone minigame table socket. game_session owns it; the gateway relays frames."""
    await relay_websocket(websocket, service="game_session", segments=("ws", "minigames", table_id))
