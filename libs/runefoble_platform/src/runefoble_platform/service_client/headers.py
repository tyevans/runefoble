"""Build the headers that a service client sends to an owning bounded context.

Only three kinds of header leave the caller: the verified `Authorization` value, the
service credential (ADR-0015 e), and the W3C trace context from the active span.
Client headers are never copied. Each owning service verifies the bearer token itself
(ADR-0015, decision c).
"""

from __future__ import annotations

from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from runefoble_platform.telemetry import inject_trace_context


def build_upstream_headers(authorization: str | None, service_credential: str) -> dict[str, str]:
    """Return the outgoing headers for one call.

    `authorization` is the verified bearer header of the caller. When it is None,
    no `Authorization` header is sent. `service_credential` is sent on every call.
    The `traceparent` header comes from the active OpenTelemetry context, if a span is active.
    """
    headers: dict[str, str] = {SERVICE_CREDENTIAL_HEADER: service_credential}
    if authorization:
        headers["Authorization"] = authorization
    return inject_trace_context(headers)
