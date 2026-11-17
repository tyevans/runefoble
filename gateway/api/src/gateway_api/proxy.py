"""Forward gateway requests to owning services with the caller's verified bearer token.

A proxy route runs only after the gateway verifies the bearer token. This module
forwards that same `Authorization` header to the owning service, which verifies
the token again. It never forwards any other identity header from the client.

Failure contract:
- Connection failure, timeout, invalid JSON, or upstream 5xx returns HTTP 502
  with a fixed message. The gateway never substitutes local data.
- Upstream 4xx (for example 401 or 403) passes through with its status code.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any

import httpx
from fastapi import HTTPException, Request, status

logger = logging.getLogger("runefoble.gateway.proxy")

UPSTREAM_UNAVAILABLE_DETAIL = "Upstream service is unavailable"
UPSTREAM_INVALID_DETAIL = "Upstream service returned an invalid response"
UPSTREAM_NOT_CONFIGURED_DETAIL = "Upstream service is not configured"


def upstream_url(env_name: str, default: str | None = None) -> str:
    """Read an upstream base URL at call time. Return 503 when it is not set and has no default."""
    value = os.environ.get(env_name, default)
    if not value:
        logger.error("Upstream URL setting %s is not configured", env_name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=UPSTREAM_NOT_CONFIGURED_DETAIL,
        )
    return value


def _upstream_error_detail(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


async def forward_json(
    request: Request,
    *,
    method: str,
    base_url: str,
    path: str,
    json_body: Any = None,
    params: Mapping[str, str] | None = None,
    timeout: float = 5.0,
) -> Any:
    """Send one request to an owning service and return its decoded JSON body.

    The caller's `Authorization` header is copied. No other header from the
    client is forwarded.
    """
    headers: dict[str, str] = {}
    authorization = request.headers.get("authorization")
    if authorization:
        headers["Authorization"] = authorization

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                f"{base_url}{path}",
                json=json_body,
                params=dict(params) if params else None,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        logger.warning("Upstream unreachable: %s %s (%s)", method, path, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=UPSTREAM_UNAVAILABLE_DETAIL
        ) from exc

    if response.status_code >= 500:
        logger.warning("Upstream error: %s %s returned %d", method, path, response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=UPSTREAM_UNAVAILABLE_DETAIL
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=_upstream_error_detail(response),
        )

    try:
        return response.json()
    except ValueError as exc:
        logger.warning("Upstream returned non-JSON body: %s %s", method, path)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=UPSTREAM_INVALID_DETAIL
        ) from exc
