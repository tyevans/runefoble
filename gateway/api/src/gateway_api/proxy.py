"""Forward gateway requests to owning services with the caller's verified bearer token.

A proxy route runs only after the gateway verifies the bearer token. The helper
sends that same `Authorization` value to the owning service, which verifies the
token again (ADR-0015, decision c). It sends no other client header.

All calls go through the shared `ServiceClient` held by `UpstreamRegistry`.
Failure contract (see `upstream_errors.py`):
- Connect failure, timeout, or no configured URL returns 503.
- Upstream 5xx returns 502.
- Upstream 4xx passes through with its status and body.
- A 2xx answer that is not JSON returns 502.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request, status
from gateway_api.dependencies import get_upstreams
from gateway_api.upstream_errors import UpstreamRejectedError

logger = logging.getLogger("runefoble.gateway.proxy")

UPSTREAM_INVALID_DETAIL = "Upstream service returned an invalid response"


async def forward_json(
    request: Request,
    *,
    service: str,
    method: str,
    path: str,
    json_body: Any = None,
    params: Mapping[str, str] | None = None,
    timeout: float = 5.0,
) -> Any:
    """Send one request to an owning service and return its decoded JSON body."""
    client = get_upstreams(request).client(service)
    reply = await client.send(
        method,
        path,
        authorization=request.headers.get("authorization"),
        json=json_body,
        params=dict(params) if params else None,
        timeout_s=timeout,
    )

    if reply.status_code >= 400:
        raise UpstreamRejectedError(service, reply)

    try:
        return json.loads(reply.body)
    except ValueError as exc:
        logger.warning("Upstream %s returned a non-JSON body: %s %s", service, method, path)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=UPSTREAM_INVALID_DETAIL
        ) from exc
