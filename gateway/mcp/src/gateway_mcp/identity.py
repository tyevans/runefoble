"""Verified caller identity for the gateway MCP process (TASK-0532, ADR-0015 c).

The streamable HTTP transport requires a bearer token on every request. `BearerTransportAuth`
verifies it before the MCP server dispatches anything. The verified principal travels with
the request, so a tool reads the caller from its own request context. Identity never comes
from a header, a query string, or a request body.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import anyio
from fastapi import HTTPException
from runefoble_auth.principal import (
    BearerVerifier,
    VerifiedPrincipal,
    authenticate_authorization,
)
from runefoble_auth.wiring import make_verifier_holder, verifier_from_settings
from runefoble_platform.config import PlatformSettings
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("runefoble.gateway_mcp.identity")

PUBLIC_PATHS = frozenset({"/healthz"})

# The verifier for this process, built from platform settings on first use. Tests replace it.
get_verifier, set_verifier = make_verifier_holder(
    lambda: verifier_from_settings(PlatformSettings())
)


class BearerTransportAuth:
    """ASGI wrapper that refuses every non-public HTTP request without a verified bearer token.

    The check runs before the wrapped application sees the request, so no MCP message is
    dispatched to a tool for an unauthenticated caller. The verified principal is stored in
    the request state under `principal`.
    """

    def __init__(
        self,
        app: ASGIApp,
        verifier: Callable[[], BearerVerifier] = get_verifier,
    ) -> None:
        self._app = app
        self._verifier = verifier

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in PUBLIC_PATHS:
            await self._app(scope, receive, send)
            return
        authorization = Headers(scope=scope).get("authorization")
        try:
            principal = await anyio.to_thread.run_sync(
                authenticate_authorization, self._verifier(), authorization
            )
        except HTTPException as exc:
            logger.warning("MCP transport refused %s: %s", scope["path"], exc.status_code)
            response = JSONResponse(
                {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
            )
            await response(scope, receive, send)
            return
        scope.setdefault("state", {})["principal"] = principal
        await self._app(scope, receive, send)


def caller_principal(ctx: Any | None) -> VerifiedPrincipal | None:
    """Return the verified principal of the MCP request behind `ctx`, or None without one."""
    if ctx is None:
        return None
    try:
        request = ctx.request_context.request
    except ValueError:
        return None
    if request is None:
        return None
    principal = getattr(request.state, "principal", None)
    return principal if isinstance(principal, VerifiedPrincipal) else None


def current_caller_id(mcp: Any | None) -> str | None:
    """Return the verified user id of the MCP request that is running now, or None."""
    if mcp is None:
        return None
    principal = caller_principal(mcp.get_context())
    return principal.user_id if principal is not None else None
