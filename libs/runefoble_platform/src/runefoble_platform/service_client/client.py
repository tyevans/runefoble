"""Typed HTTP client for calls from a gateway to one owning bounded context.

One `ServiceClient` wraps one `httpx.AsyncClient` for one service base URL. The
caller sets the timeout for each call. The client adds no retries and no cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from runefoble_platform.service_client.errors import (
    UpstreamFailureError,
    UpstreamUnavailableError,
)
from runefoble_platform.service_client.headers import build_upstream_headers

DEFAULT_CONTENT_TYPE = "application/json"


@dataclass(frozen=True)
class UpstreamReply:
    """A 2xx or 4xx answer from an owning service, returned unchanged."""

    status_code: int
    content_type: str
    body: bytes
    # The upstream authentication challenge. A 401 must carry it (RFC 9110, section 11.6.1).
    www_authenticate: str | None = None


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
        self._http = httpx.AsyncClient(transport=transport)

    async def send(
        self,
        method: str,
        path: str,
        *,
        authorization: str | None,
        timeout_s: float,
        json: Any = None,
        params: dict[str, str] | None = None,
    ) -> UpstreamReply:
        """Send one request and return the upstream reply.

        Raises UpstreamUnavailableError on connect failure or timeout.
        Raises UpstreamFailureError on an upstream 5xx status.
        """
        try:
            response = await self._http.request(
                method,
                f"{self._base_url}{path}",
                json=json,
                params=params,
                headers=build_upstream_headers(authorization, self._service_credential),
                timeout=timeout_s,
            )
        except httpx.TransportError as exc:
            raise UpstreamUnavailableError(self.service, type(exc).__name__) from exc

        if response.status_code >= 500:
            raise UpstreamFailureError(self.service, response.status_code, response.content)

        return UpstreamReply(
            status_code=response.status_code,
            content_type=response.headers.get("content-type", DEFAULT_CONTENT_TYPE),
            body=response.content,
            www_authenticate=response.headers.get("www-authenticate"),
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
