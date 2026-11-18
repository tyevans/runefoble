"""Read the MCP caller's bearer token from the MCP request, when the transport carries one."""

from typing import Any


def caller_bearer(ctx: Any | None) -> str | None:
    """Return the bearer token of the MCP request, or None when the request carries none.

    The gateway never invents a credential. A missing token stays missing, and the
    upstream service decides whether the call is allowed.
    """
    if ctx is None:
        return None
    try:
        request = ctx.request_context.request
    except ValueError:
        return None
    if request is None:
        return None
    header = str(request.headers.get("authorization", ""))
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()
