"""Gateway proxy for the audience routes owned by audience_studio (TASK-0439).

The gateway verifies the bearer token, then forwards each request with that same token to
audience_studio. audience_studio verifies the token again and checks every permission in
`runefoble.zed` (`audience_poll.view`, `vote`, `moderate`, `approve`, `veto`). The gateway keeps no
audience state, adds no permission check, and does not parse the payload. Each REST route is a row
in `ROUTES` (TASK-0822). The live audience socket is relayed to the owner's `/ws/audience/...`.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes
from gateway_api.websocket_relay import relay_websocket

AUDIENCE_SERVICE = "audience_studio"

router = APIRouter(tags=["Audience"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/audience/polls",
        ("api", "v1", "audience", "polls"),
        AUDIENCE_SERVICE,
        name="create_audience_poll",
        doc="Create a chaos poll. audience_studio checks `run_session` on the campaign.",
        reply="bytes",
        body="raw",
        status_code=201,
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/audience/polls",
        ("api", "v1", "audience", "polls"),
        AUDIENCE_SERVICE,
        name="list_audience_polls",
        doc="List polls the caller can view. The query string reaches the owner unchanged.",
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/audience/polls/{poll_id}",
        ("api", "v1", "audience", "polls", "{poll_id}"),
        AUDIENCE_SERVICE,
        name="get_audience_poll",
        doc="Read a poll with its live tallies. audience_studio checks `view`.",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/audience/polls/{poll_id}/votes",
        ("api", "v1", "audience", "polls", "{poll_id}", "votes"),
        AUDIENCE_SERVICE,
        name="cast_audience_vote",
        doc="Cast a spectator vote. audience_studio checks `vote`; the voter is the token subject.",
        reply="bytes",
        body="raw",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/audience/polls/{poll_id}/close",
        ("api", "v1", "audience", "polls", "{poll_id}", "close"),
        AUDIENCE_SERVICE,
        name="close_audience_poll",
        doc="Close a poll and resolve its proposals. audience_studio checks `moderate`.",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/audience/proposals",
        ("api", "v1", "audience", "proposals"),
        AUDIENCE_SERVICE,
        name="list_audience_proposals",
        doc="List modifier proposals. audience_studio checks `view` and filters by `approve`.",
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/audience/proposals/{proposal_id}/approve",
        ("api", "v1", "audience", "proposals", "{proposal_id}", "approve"),
        AUDIENCE_SERVICE,
        name="approve_audience_proposal",
        doc="Approve a chaos modifier. audience_studio checks `approve`.",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/audience/proposals/{proposal_id}/veto",
        ("api", "v1", "audience", "proposals", "{proposal_id}", "veto"),
        AUDIENCE_SERVICE,
        name="veto_audience_proposal",
        doc="Veto a chaos modifier. audience_studio checks `veto`.",
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)


@router.websocket("/ws/audience/{campaign_id}")
async def audience_websocket(websocket: WebSocket, campaign_id: str) -> None:
    """Live audience stream. audience_studio checks `view` on the campaign during the handshake."""
    await relay_websocket(
        websocket, service=AUDIENCE_SERVICE, segments=("ws", "audience", campaign_id)
    )
