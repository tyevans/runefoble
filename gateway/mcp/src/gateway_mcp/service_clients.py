"""Shared service clients of the gateway MCP process, one pool per container (TASK-0746).

The HTTP connections of a client belong to the event loop that opened them. The pool keeps
one client per event loop, service, base URL, and credential. Its entries end with their loop.
"""

from __future__ import annotations

import asyncio
import weakref

from runefoble_platform.service_client import ServiceClient


class ServiceClientPool:
    """Hands out the shared `ServiceClient` of the running event loop."""

    def __init__(self) -> None:
        self._by_loop: weakref.WeakKeyDictionary[
            asyncio.AbstractEventLoop, dict[tuple[str, str, str], ServiceClient]
        ] = weakref.WeakKeyDictionary()

    def client(self, service: str, base_url: str, credential: str) -> ServiceClient:
        """Return the client for one service of the running loop, creating it on first use."""
        clients = self._by_loop.setdefault(asyncio.get_running_loop(), {})
        key = (service, base_url, credential)
        client = clients.get(key)
        if client is None:
            client = ServiceClient(service, base_url, credential)
            clients[key] = client
        return client
