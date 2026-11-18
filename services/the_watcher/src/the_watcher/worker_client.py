"""HTTP client for the inference worker. Every worker failure becomes an explicit HTTP error.

The Watcher never replaces a failed worker call with canned output. A failure is raised as
HTTP 503 (backend unavailable) or HTTP 502 (unexpected worker status).
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from the_watcher.dependencies import logger, platform_settings


def _service_credential_header() -> dict[str, str]:
    """Return the service credential header (ADR-0015 e). Refuse the call when none is set."""
    credential = platform_settings.service_credential
    if credential is None or not credential.get_secret_value().strip():
        logger.error("RUNEFOBLE_SERVICE_CREDENTIAL is not set. The worker call is refused.")
        raise HTTPException(
            status_code=503,
            detail={"error": "backend_unavailable", "backend": "inference_worker"},
        )
    return {SERVICE_CREDENTIAL_HEADER: credential.get_secret_value()}


async def call_worker(
    base_url: str, path: str, payload: dict[str, Any], *, timeout: float
) -> dict[str, Any]:
    """POST a payload to the inference worker and return its JSON object."""
    headers = _service_credential_header()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{base_url}{path}", json=payload, headers=headers)
    except httpx.HTTPError as e:
        logger.error("Inference worker unreachable at %s: %s", base_url, e)
        raise HTTPException(
            status_code=503,
            detail={"error": "backend_unavailable", "backend": "inference_worker"},
        ) from e

    if res.status_code == 503:
        backend = res.json().get("backend", "unknown")
        logger.error("Inference worker reported backend '%s' unavailable", backend)
        raise HTTPException(
            status_code=503,
            detail={"error": "backend_unavailable", "backend": backend},
        )
    if res.status_code != 200:
        logger.error("Inference worker returned HTTP %s for %s", res.status_code, path)
        raise HTTPException(
            status_code=502,
            detail={"error": "inference_worker_error", "status": res.status_code},
        )
    data: dict[str, Any] = res.json()
    return data
