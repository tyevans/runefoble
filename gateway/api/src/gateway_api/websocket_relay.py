"""Relay one WebSocket from a gateway client to the owning service (TASK-0592).

The gateway checks the bearer token before it relays (ADR-0015 b, c). It then opens an
upstream socket to the owning service with the same path and the same offered subprotocols,
so the bearer subprotocol reaches the owner. The owner verifies the token again and checks
object permissions. The relay does not parse frames and adds no permission check. The query string passes to the
owner unchanged, so presentation fields such as `peer_id` reach it.

Close codes the client sees:
- Gateway token check fails: 1008, closed before accept (as `admit_websocket` does).
- Owner refuses the handshake with HTTP 401: 1008. With HTTP 403: 4403 (authorization refusal).
- Owner unreachable or slow to open: 1013 (try again later). Any other handshake failure: 1011.
- A close from either side passes to the other side with the same code and reason.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.auth import get_zitadel_auth_service
from gateway_api.dependencies import get_upstreams
from runefoble_auth.websocket import WS_POLICY_VIOLATION, WebSocketAuthError, authenticate_websocket
from runefoble_platform.service_client import UpstreamUnavailableError, path
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidStatus

logger = logging.getLogger("runefoble.gateway.websocket_relay")

OPEN_TIMEOUT_S = 5.0
CLIENT_CLOSE_GRACE_S = 1.0
MAX_FRAME_BYTES = 8 * 1024 * 1024
CLOSE_FORBIDDEN_CODE = 4403
CLOSE_TRY_AGAIN_LATER = 1013
CLOSE_INTERNAL_ERROR = 1011
CLOSE_GOING_AWAY = 1001
CLOSE_NO_STATUS = 1005
CLOSE_ABNORMAL = 1006
CLOSE_SERVICE_RESTART_OR_FAIL = 1015

Side = Literal["client", "owner"]


async def relay_websocket(websocket: WebSocket, *, service: str, segments: tuple[str, ...]) -> None:
    """Authenticate the caller, open the owner socket at `segments`, and relay frames both ways."""
    try:
        authenticate_websocket(websocket, get_zitadel_auth_service())
    except WebSocketAuthError as exc:
        logger.warning("WebSocket handshake denied on %s: %s", websocket.url.path, exc)
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    try:
        owner_path = path(*segments)
    except ValueError:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    offered = list(websocket.scope.get("subprotocols", []))
    try:
        target, headers = get_upstreams(websocket).client(service).websocket_target(owner_path)
        if websocket.url.query:
            target = f"{target}?{websocket.url.query}"
        upstream = await connect(
            target,
            subprotocols=offered or None,
            additional_headers=headers,
            open_timeout=OPEN_TIMEOUT_S,
            max_size=MAX_FRAME_BYTES,
            compression=None,
        )
    except (UpstreamUnavailableError, OSError, TimeoutError) as exc:
        logger.warning("Upstream %s socket unavailable: %s", service, type(exc).__name__)
        await _refuse(websocket, CLOSE_TRY_AGAIN_LATER)
        return
    except InvalidStatus as exc:
        code = _refusal_code(exc.response.status_code)
        logger.warning("Upstream %s refused the socket: HTTP %d", service, exc.response.status_code)
        await _refuse(websocket, code)
        return
    except InvalidHandshake:
        logger.warning("Upstream %s returned an invalid handshake", service)
        await _refuse(websocket, CLOSE_INTERNAL_ERROR)
        return

    await websocket.accept(subprotocol=upstream.subprotocol)
    await _relay_frames(websocket, upstream)


def _refusal_code(status_code: int) -> int:
    if status_code == 401:
        return WS_POLICY_VIOLATION
    if status_code == 403:
        return CLOSE_FORBIDDEN_CODE
    return CLOSE_INTERNAL_ERROR


async def _refuse(websocket: WebSocket, code: int) -> None:
    """Accept, then close with `code`. A close code cannot be sent before accept."""
    await websocket.accept()
    await websocket.close(code=code)


async def _relay_frames(websocket: WebSocket, upstream: ClientConnection) -> None:
    client_task = asyncio.create_task(_client_to_owner(websocket, upstream))
    owner_task = asyncio.create_task(_owner_to_client(websocket, upstream))
    try:
        done, _ = await asyncio.wait({client_task, owner_task}, return_when=asyncio.FIRST_COMPLETED)
        ended_by, code, reason = next(iter(done)).result()
        if ended_by == "owner":
            await websocket.close(code=code, reason=reason)
            # Let the pending client receive end on the client's close, instead of cancelling it.
            await asyncio.wait({client_task}, timeout=CLIENT_CLOSE_GRACE_S)
        else:
            await upstream.close(code=code, reason=reason)
    except BaseException:
        await upstream.close()
        raise
    finally:
        for task in (client_task, owner_task):
            task.cancel()
        await asyncio.gather(client_task, owner_task, return_exceptions=True)


async def _client_to_owner(
    websocket: WebSocket, upstream: ClientConnection
) -> tuple[Side, int, str]:
    """Forward client frames to the owner. Return who ended the relay and the close to pass on."""
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return "client", _sendable(message.get("code", CLOSE_NO_STATUS)), ""
            if message.get("text") is not None:
                await upstream.send(message["text"])
            elif message.get("bytes") is not None:
                await upstream.send(message["bytes"])
    except ConnectionClosed:
        return ("owner", *_owner_close(upstream))


async def _owner_to_client(
    websocket: WebSocket, upstream: ClientConnection
) -> tuple[Side, int, str]:
    """Forward owner frames to the client. Return who ended the relay and the close to pass on."""
    try:
        async for frame in upstream:
            if isinstance(frame, str):
                await websocket.send_text(frame)
            else:
                await websocket.send_bytes(frame)
    except ConnectionClosed:
        pass
    except WebSocketDisconnect:
        return "client", CLOSE_GOING_AWAY, ""
    return ("owner", *_owner_close(upstream))


def _owner_close(upstream: ClientConnection) -> tuple[int, str]:
    return _sendable(upstream.close_code or CLOSE_NO_STATUS), upstream.close_reason or ""


def _sendable(code: int) -> int:
    """Map a code that the peer may not send (no status, abnormal) to one that may be sent."""
    if code == CLOSE_NO_STATUS:
        return 1000
    if code in (CLOSE_ABNORMAL, CLOSE_SERVICE_RESTART_OR_FAIL):
        return CLOSE_INTERNAL_ERROR
    return code


__all__ = ["relay_websocket"]
