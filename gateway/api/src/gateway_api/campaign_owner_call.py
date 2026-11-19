"""Send one campaign socket action to its owner and turn the owner's answer into a frame (TASK-0883).

The owner decides. A 2xx answer means the owner applied the action. A refusal or a failed owner
becomes a typed error frame. The gateway never fills in a value that the owner did not return
(ADR-0015 b).
"""

from __future__ import annotations

from fastapi import WebSocket
from gateway_api.campaign_actions import OwnerCall
from gateway_api.dependencies import get_upstreams
from runefoble_auth.websocket import send_socket_error
from runefoble_platform.service_client import (
    UpstreamFailureError,
    UpstreamUnavailableError,
    error_detail,
)

OWNER_TIMEOUT_S = 5.0

# The owner status that maps to a named frame code. Any other 4xx is REJECTED.
_REFUSAL_CODES = {403: "PERMISSION_DENIED", 404: "NOT_FOUND"}


async def send_owner_call(websocket: WebSocket, action: str, call: OwnerCall, token: str) -> bool:
    """Call the owner with the caller's token. Return True when it applied the action.

    Otherwise send one error frame and return False.
    """
    try:
        client = get_upstreams(websocket).client(call.service)
        reply = await client.send(
            call.route.method,
            call.route.path,
            authorization=f"Bearer {token}",
            json=call.body,
            timeout_s=OWNER_TIMEOUT_S,
        )
    except UpstreamUnavailableError as exc:
        message = f"{call.service} is unavailable for action '{action}': {exc.reason}"
        await send_socket_error(websocket, "UPSTREAM_UNAVAILABLE", message, action=action)
        return False
    except UpstreamFailureError as exc:
        message = f"{call.service} failed for action '{action}' ({exc.status_code})"
        await send_socket_error(
            websocket,
            "UPSTREAM_UNAVAILABLE",
            message,
            action=action,
            status_code=exc.status_code,
        )
        return False

    if reply.status_code < 400:
        return True
    code = _REFUSAL_CODES.get(reply.status_code, "REJECTED")
    message = (
        f"{call.service} refused action '{action}' ({reply.status_code}): "
        f"{error_detail(reply.body)}"
    )
    await send_socket_error(websocket, code, message, action=action, status_code=reply.status_code)
    return False


__all__ = ["OWNER_TIMEOUT_S", "send_owner_call"]
