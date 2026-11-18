"""Service-to-service credential (ADR-0015 e).

A calling service presents `X-Runefoble-Service-Credential` on a call to another service.
The value comes from the `RUNEFOBLE_SERVICE_CREDENTIAL` setting, which Helm reads from a
Kubernetes Secret. The header never carries a user token. Receivers compare the value in
constant time. A service with no credential does not start.
"""

from __future__ import annotations

import hmac

from runefoble_platform.config import PlatformSettings

SERVICE_CREDENTIAL_HEADER = "X-Runefoble-Service-Credential"


def service_credential_matches(presented: str | None, expected: str) -> bool:
    """Return True only when both values are present and equal. Compares in constant time."""
    if not presented or not expected:
        return False
    return hmac.compare_digest(presented.encode(), expected.encode())


def expected_service_credential() -> str:
    """Return the configured service credential. Raise at start-up when it is unset or blank."""
    credential = PlatformSettings().service_credential
    value = credential.get_secret_value().strip() if credential is not None else ""
    if not value:
        raise RuntimeError(
            "RUNEFOBLE_SERVICE_CREDENTIAL is not set. The service refuses to start (ADR-0015 e)."
        )
    return value
