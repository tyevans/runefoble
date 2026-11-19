"""Port that forwards a player transcript to The Watcher and reports the result (TASK-0732).

The voice pipeline sends each transcript to `POST /api/v1/watcher/transcribe-and-act` with the
speaker's own bearer (ADR-0015 c). The port never raises for a Watcher failure. It returns an
`IntentForwardResult` that holds either the intent or an error text, so the caller can report
the failure to the client. It never returns a substitute intent (ADR-0015 b).
"""

from __future__ import annotations

import asyncio
import json
import weakref
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from runefoble_platform.config import PlatformSettings
from runefoble_platform.service_client import (
    ServiceClient,
    UpstreamFailureError,
    UpstreamUnavailableError,
)
from runefoble_platform.service_credential import expected_service_credential

WATCHER_SERVICE = "the_watcher"
TRANSCRIBE_AND_ACT_PATH = "/api/v1/watcher/transcribe-and-act"
WATCHER_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class IntentForwardResult:
    """The Watcher intent, or the reason that forwarding failed. Exactly one field is set."""

    intent: dict[str, Any] | None = None
    error: str | None = None


class WatcherIntentPort(Protocol):
    """Forwards one transcript payload to The Watcher."""

    async def forward(
        self, payload: dict[str, Any], caller_authorization: str | None
    ) -> IntentForwardResult: ...


class UnconfiguredWatcherIntent:
    """Used when no Watcher URL is set. Every forward reports the missing setting."""

    async def forward(
        self, payload: dict[str, Any], caller_authorization: str | None
    ) -> IntentForwardResult:
        return IntentForwardResult(error="RUNEFOBLE_WATCHER_URL is not set")


class ServiceClientWatcherIntent:
    """Forwards transcripts through the shared `ServiceClient`.

    The HTTP connections of a client belong to the event loop that opened them, so the adapter
    keeps one client for each running loop. A client ends with its loop.
    """

    def __init__(
        self,
        base_url: str,
        service_credential: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_s: float = WATCHER_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url
        self._service_credential = service_credential
        self._transport = transport
        self._timeout_s = timeout_s
        self._clients: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, ServiceClient] = (
            weakref.WeakKeyDictionary()
        )

    def _client(self) -> ServiceClient:
        loop = asyncio.get_running_loop()
        client = self._clients.get(loop)
        if client is None:
            client = ServiceClient(
                WATCHER_SERVICE, self._base_url, self._service_credential, self._transport
            )
            self._clients[loop] = client
        return client

    async def forward(
        self, payload: dict[str, Any], caller_authorization: str | None
    ) -> IntentForwardResult:
        try:
            reply = await self._client().send(
                "POST",
                TRANSCRIBE_AND_ACT_PATH,
                authorization=caller_authorization,
                timeout_s=self._timeout_s,
                json=payload,
            )
        except UpstreamUnavailableError as exc:
            return IntentForwardResult(error=f"the_watcher is unreachable ({exc.reason})")
        except UpstreamFailureError as exc:
            return IntentForwardResult(error=f"the_watcher failed with HTTP {exc.status_code}")

        if reply.status_code != 200:
            return IntentForwardResult(
                error=f"the_watcher refused the transcript with HTTP {reply.status_code}"
            )
        try:
            intent = json.loads(reply.body)
        except ValueError:
            return IntentForwardResult(error="the_watcher returned a body that is not JSON")
        if not isinstance(intent, dict):
            return IntentForwardResult(error="the_watcher returned a body that is not an object")
        return IntentForwardResult(intent=intent)


def build_watcher_intent_port(settings: PlatformSettings) -> WatcherIntentPort:
    """Build the Watcher port from the settings. Raise when the service credential is unset."""
    base_url = (settings.the_watcher_url or "").strip()
    if not base_url:
        return UnconfiguredWatcherIntent()
    return ServiceClientWatcherIntent(base_url, expected_service_credential(settings))


__all__ = [
    "IntentForwardResult",
    "ServiceClientWatcherIntent",
    "UnconfiguredWatcherIntent",
    "WatcherIntentPort",
    "build_watcher_intent_port",
]
