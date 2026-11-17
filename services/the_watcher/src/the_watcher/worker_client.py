"""HTTP client for the inference worker. Every worker failure becomes an explicit HTTP error.

The Watcher never replaces a failed worker call with canned output. A failure is raised as
HTTP 503 (backend unavailable) or HTTP 502 (unexpected worker status).
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from the_watcher.dependencies import logger


async def call_worker(
    base_url: str, path: str, payload: dict[str, Any], *, timeout: float
) -> dict[str, Any]:
    """POST a payload to the inference worker and return its JSON object."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{base_url}{path}", json=payload)
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
