"""HTTP mapping for failed gateway calls to owning services.

- UpstreamUnavailableError -> 503 with `{"detail", "upstream"}`.
- UpstreamFailureError (upstream 5xx) -> 502 with `{"detail", "upstream"}`.
- UpstreamRejectedError (upstream 4xx) -> the upstream status and body, unchanged.

Each failure logs at warning level. The gateway never returns a substitute value.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from runefoble_platform.service_client import (
    UpstreamFailureError,
    UpstreamReply,
    UpstreamUnavailableError,
)

logger = logging.getLogger("runefoble.gateway.upstream")

UPSTREAM_UNAVAILABLE_DETAIL = "Upstream service is unavailable"


class UpstreamRejectedError(Exception):
    """An owning service answered 4xx. The gateway passes that answer on unchanged."""

    def __init__(self, service: str, reply: UpstreamReply) -> None:
        super().__init__(f"Upstream {service} rejected the request: HTTP {reply.status_code}")
        self.service = service
        self.reply = reply


async def _unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, UpstreamUnavailableError)
    logger.warning("Upstream %s unavailable: %s", exc.service, exc.reason)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": UPSTREAM_UNAVAILABLE_DETAIL, "upstream": exc.service},
    )


async def _failure_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, UpstreamFailureError)
    logger.warning("Upstream %s failed with HTTP %d", exc.service, exc.status_code)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": UPSTREAM_UNAVAILABLE_DETAIL, "upstream": exc.service},
    )


async def _rejected_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, UpstreamRejectedError)
    return Response(
        content=exc.reply.body,
        status_code=exc.reply.status_code,
        media_type=exc.reply.content_type,
    )


def register_upstream_error_handlers(app: FastAPI) -> None:
    """Attach the upstream failure mapping to a FastAPI app."""
    app.add_exception_handler(UpstreamUnavailableError, _unavailable_handler)
    app.add_exception_handler(UpstreamFailureError, _failure_handler)
    app.add_exception_handler(UpstreamRejectedError, _rejected_handler)
