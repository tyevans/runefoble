"""Build the headers that a service client sends to an owning bounded context.

Only two kinds of header leave the caller: the verified `Authorization` value and
the W3C trace context from the active span. Client headers are never copied. Each
owning service verifies the bearer token itself (ADR-0015, decision c).
"""

from __future__ import annotations

from runefoble_platform.telemetry import inject_trace_context


def build_upstream_headers(authorization: str | None) -> dict[str, str]:
    """Return the outgoing headers for one call.

    `authorization` is the verified bearer header of the caller. When it is None,
    no `Authorization` header is sent. The `traceparent` header comes from the
    active OpenTelemetry context, if a span is active.
    """
    headers: dict[str, str] = {}
    if authorization:
        headers["Authorization"] = authorization
    return inject_trace_context(headers)
