"""HTTP client for the inference worker. Every worker failure becomes an explicit error.

The Watcher never replaces a failed worker call with canned output. An unavailable worker
raises `EngineUnavailableError` (HTTP 503). An unexpected worker status raises HTTP 502.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import SecretStr
from runefoble_platform.engine_ports import EngineUnavailableError
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from the_watcher.dependencies import logger

WORKER_ENGINE = "inference_worker"


def _unavailable(message: str, backend: str = WORKER_ENGINE) -> EngineUnavailableError:
    return EngineUnavailableError("backend_unavailable", backend, message, engine_field="backend")


def _service_credential_header(credential: SecretStr | None) -> dict[str, str]:
    """Return the service credential header (ADR-0015 e). Refuse the call when none is set."""
    if credential is None or not credential.get_secret_value().strip():
        raise _unavailable("RUNEFOBLE_SERVICE_CREDENTIAL is not set. The worker call is refused.")
    return {SERVICE_CREDENTIAL_HEADER: credential.get_secret_value()}


async def call_worker(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float,
    credential: SecretStr | None,
) -> dict[str, Any]:
    """POST a payload to the inference worker and return its JSON object.

    `credential` is `RUNEFOBLE_SERVICE_CREDENTIAL`. Without it the call is refused with 503.
    """
    headers = _service_credential_header(credential)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{base_url}{path}", json=payload, headers=headers)
    except httpx.HTTPError as e:
        logger.error("Inference worker unreachable at %s: %s", base_url, e)
        raise _unavailable(f"The inference worker at {base_url} is unreachable.") from e

    if res.status_code == 503:
        backend = res.json().get("backend", "unknown")
        logger.error("Inference worker reported backend '%s' unavailable", backend)
        raise _unavailable(
            f"The inference worker reports backend '{backend}' unavailable.", backend
        )
    if res.status_code != 200:
        logger.error("Inference worker returned HTTP %s for %s", res.status_code, path)
        raise HTTPException(
            status_code=502,
            detail={"error": "inference_worker_error", "status": res.status_code},
        )
    data: dict[str, Any] = res.json()
    return data
