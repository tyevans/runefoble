"""Invite account route at the gateway (ADR-0023 b, d).

The route takes no bearer token. The gateway checks two rate limits, one for the client address
and one for the invite, and then forwards the body to game_session without any credential. It
keeps no campaign or account state. Upstream replies map as in `upstream_errors.py`, except
that a 503 from game_session (the account provider is unavailable) stays 503.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from gateway_api.account_invite_limits import (
    AccountInviteLimits,
    client_limit_key,
    invite_limit_key,
)
from gateway_api.dependencies import get_upstreams
from gateway_api.models import CreateAccountRequest
from gateway_api.proxy import decode_upstream_json
from gateway_api.upstream_errors import UpstreamRejectedError
from runefoble_platform.rate_limit import RateDecision
from runefoble_platform.service_client import UpstreamFailureError, path

SERVICE = "game_session"
UPSTREAM_TIMEOUT_S = 5.0
ACCOUNT_UNAVAILABLE_DETAIL = "Account creation is unavailable"

router = APIRouter(tags=["Campaigns & Sessions"])


@router.post(
    "/api/v1/campaigns/invites/{token}/accounts",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_account_from_invite(
    token: str, req: CreateAccountRequest, request: Request
) -> Any:
    """Create a player account through a campaign invite. Zitadel emails the person.

    Returns 202 with the same body for a new and an existing email. Requires no bearer token.
    """
    limits: AccountInviteLimits = request.app.state.account_invite_limits
    address = request.client.host if request.client else "unknown"
    decisions = (
        limits.client.hit(client_limit_key(address)),
        limits.invite.hit(invite_limit_key(token)),
    )
    refused = [decision for decision in decisions if not decision.allowed]
    if refused:
        return _too_many_requests(refused)

    try:
        owner_path = path("api", "v1", "campaigns", "invites", token, "accounts")
    except ValueError:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not Found"})

    client = get_upstreams(request).client(SERVICE)
    try:
        reply = await client.send(
            "POST",
            owner_path,
            authorization=None,
            json=req.model_dump(),
            timeout_s=UPSTREAM_TIMEOUT_S,
        )
    except UpstreamFailureError as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": ACCOUNT_UNAVAILABLE_DETAIL, "upstream": SERVICE},
            )
        raise
    if reply.status_code >= status.HTTP_400_BAD_REQUEST:
        raise UpstreamRejectedError(SERVICE, reply)
    return decode_upstream_json(SERVICE, "POST", owner_path, reply.body)


def _too_many_requests(refused: list[RateDecision]) -> JSONResponse:
    retry_after = max(decision.retry_after_seconds for decision in refused)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Try again later."},
        headers={"Retry-After": str(retry_after)},
    )
