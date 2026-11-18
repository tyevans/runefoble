"""Service credential guard for inference worker routes (ADR-0015 e).

Callers are other services, never browsers. Each request presents the shared service
credential in the `X-Runefoble-Service-Credential` header. The comparison is constant time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Header, HTTPException
from runefoble_platform.service_credential import (
    SERVICE_CREDENTIAL_HEADER,
    service_credential_matches,
)


def service_credential_guard(expected_credential: str) -> Callable[..., None]:
    """Build a dependency that accepts only the configured service credential. No fallback."""

    def _guard(
        service_credential: Annotated[str | None, Header(alias=SERVICE_CREDENTIAL_HEADER)] = None,
    ) -> None:
        if not service_credential_matches(service_credential, expected_credential):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": "Missing or invalid service credential",
                },
            )

    return _guard
