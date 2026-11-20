"""Typed HTTP client for calls from a gateway to one owning bounded context.

One `ServiceClient` wraps one pooled `httpx.AsyncClient` for one service base URL. The
caller sets the timeout for each call. The TCP connect has a shorter limit,
`CONNECT_TIMEOUT_S`. The client adds no cache.

The client retries in one case only: an idempotent call whose pooled connection closed
before the answer (TASK-0936). It sends that call once more, on a fresh connection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from runefoble_platform.service_client.errors import (
    UpstreamFailureError,
    UpstreamUnavailableError,
)
from runefoble_platform.service_client.headers import build_upstream_headers

DEFAULT_CONTENT_TYPE = "application/json"

logger = logging.getLogger("runefoble.service_client")

# Longest wait for the TCP connect to an owning service. An in-cluster connect takes
# milliseconds. 2 s allows one lost SYN (the kernel sends it again after 1 s). A Service that
# still routes to a deleted pod drops every SYN, so without this limit the caller waits the
# full call timeout before it gets 503.
CONNECT_TIMEOUT_S = 2.0

# Longest time that an idle pooled connection stays in the pool. It must be shorter than the
# owner's keep-alive timeout, so the owner never closes a connection that the client is about
# to reuse. The service images start uvicorn with `--timeout-keep-alive 15`. A local uvicorn
# without that option uses 5 s. Audience Studio (Fastify) uses 72 s.
KEEPALIVE_EXPIRY_S = 4.0

# Methods that the client may send again (RFC 9110, section 9.2.2). No owner route honours an
# idempotency key, so POST and PATCH are never sent again.
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})

# The pooled connection closed before the answer arrived. The owner can be healthy: a restart
# leaves stale connections in the pool. A connect failure or a timeout is not in this list.
STALE_CONNECTION_ERRORS = (httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError)

# Response headers that describe the upstream transport, not the payload. The gateway drops
# them, because httpx has already decoded the body and the gateway sets its own framing.
TRANSPORT_HEADERS = frozenset(
    {
        "connection",
        "content-encoding",
        "content-length",
        "content-type",
        "keep-alive",
        "set-cookie",
        "transfer-encoding",
        "www-authenticate",
    }
)


@dataclass(frozen=True)
class UpstreamReply:
    """A 2xx or 4xx answer from an owning service, returned unchanged."""

    status_code: int
    content_type: str
    body: bytes
    # The upstream authentication challenge. A 401 must carry it (RFC 9110, section 11.6.1).
    www_authenticate: str | None = None
    # Payload headers of a 2xx answer, such as `Content-Disposition`, relayed as sent.
    relayed_headers: tuple[tuple[str, str], ...] = ()


class ServiceClient:
    """Send requests to one owning service and map its failures to errors."""

    def __init__(
        self,
        service: str,
        base_url: str,
        service_credential: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not service_credential.strip():
            raise ValueError(f"Service client {service} needs a service credential (ADR-0015 e)")
        self.service = service
        self._base_url = base_url.rstrip("/")
        self._service_credential = service_credential
        # `transport` lets a test route calls to an in-process app. Production passes none.
        self._http = httpx.AsyncClient(
            transport=transport, limits=httpx.Limits(keepalive_expiry=KEEPALIVE_EXPIRY_S)
        )
        # Keeps no idle connection, so each retry opens a new one.
        self._fresh_http = httpx.AsyncClient(
            transport=transport, limits=httpx.Limits(max_keepalive_connections=0)
        )

    async def send(
        self,
        method: str,
        path: str,
        *,
        authorization: str | None,
        timeout_s: float,
        json: Any = None,
        params: dict[str, str] | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
    ) -> UpstreamReply:
        """Send one request and return the upstream reply.

        `content` forwards a raw body unchanged (the owner parses it). Pass `json` or `content`,
        not both. `content_type` is the body's media type and is sent only with `content`.

        `timeout_s` limits each phase of the call. The connect phase waits at most
        `CONNECT_TIMEOUT_S`.

        An idempotent call whose pooled connection closes before the answer is sent once more,
        on a fresh connection. A POST or PATCH is never sent again.

        Raises UpstreamUnavailableError on connect failure, timeout, or a dropped connection.
        Raises UpstreamFailureError on an upstream 5xx status.
        """
        headers = build_upstream_headers(authorization, self._service_credential)
        if content_type is not None:
            headers["Content-Type"] = content_type
        request: dict[str, Any] = {
            "method": method,
            "url": f"{self._base_url}{path}",
            "json": json,
            "content": content,
            "params": params,
            "headers": headers,
            "timeout": httpx.Timeout(timeout_s, connect=min(CONNECT_TIMEOUT_S, timeout_s)),
        }
        try:
            try:
                response = await self._http.request(**request)
            except STALE_CONNECTION_ERRORS as exc:
                if method.upper() not in IDEMPOTENT_METHODS:
                    raise
                logger.warning(
                    "Retrying %s %s to %s on a fresh connection: %s",
                    method.upper(),
                    path,
                    self.service,
                    type(exc).__name__,
                )
                response = await self._fresh_http.request(**request)
        except httpx.TransportError as exc:
            raise UpstreamUnavailableError(self.service, type(exc).__name__) from exc

        if response.status_code >= 500:
            raise UpstreamFailureError(self.service, response.status_code, response.content)

        return UpstreamReply(
            status_code=response.status_code,
            content_type=response.headers.get("content-type", DEFAULT_CONTENT_TYPE),
            body=response.content,
            www_authenticate=response.headers.get("www-authenticate"),
            relayed_headers=tuple(
                (name, value)
                for name, value in response.headers.items()
                if name.lower() not in TRANSPORT_HEADERS
            ),
        )

    def websocket_target(self, path: str) -> tuple[str, dict[str, str]]:
        """Return the ws:// or wss:// URL and the handshake headers for one upstream socket.

        The caller passes its own subprotocols. The service credential goes on every handshake
        (ADR-0015 e). The caller's `Authorization` is never sent here: the bearer travels in
        the subprotocol list, so the owner verifies the same token that the client offered.
        """
        if self._base_url.startswith("https://"):
            url = "wss://" + self._base_url[len("https://") :]
        elif self._base_url.startswith("http://"):
            url = "ws://" + self._base_url[len("http://") :]
        else:
            raise ValueError(f"Service client {self.service} base URL needs an http(s) scheme")
        return f"{url}{path}", build_upstream_headers(None, self._service_credential)

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()
        await self._fresh_http.aclose()
