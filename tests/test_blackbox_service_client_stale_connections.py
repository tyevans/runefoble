"""Blackbox tests: the service client recovers from a stale pooled connection (TASK-0936).

After an owner restart, the client pool can hold a keep-alive connection that closes before
any response arrives. A GET, HEAD, PUT, DELETE or OPTIONS is sent again once, on a fresh
connection. A POST or PATCH is never sent again, because the owner may have applied it.

The owner is a raw loopback TCP server (`tests.helpers.stale_connection_owner`). Nothing
patches the HTTP client.

Governed by:
- TASK-0936: The Service Client Recovers From Stale Pooled Connections
- ADR-0015: an outage is reported, never hidden
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

import logging
import time

import pytest
from runefoble_platform.service_client import ServiceClient, UpstreamUnavailableError

from tests.helpers.live_services import unanswered_port_url
from tests.helpers.stale_connection_owner import stale_connection_owner

CREDENTIAL = "test-service-credential"


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "HEAD", "PUT", "DELETE", "OPTIONS"])
async def test_idempotent_call_on_a_stale_connection_is_sent_again_once(method: str) -> None:
    with stale_connection_owner() as owner:
        client = ServiceClient("game_session", owner.base_url, CREDENTIAL)
        try:
            first = await client.send(method, "/api/v1/first", authorization=None, timeout_s=5.0)
            second = await client.send(method, "/api/v1/second", authorization=None, timeout_s=5.0)
        finally:
            await client.aclose()

    assert (first.status_code, second.status_code) == (200, 200)
    assert owner.received == [
        f"{method} /api/v1/first",
        f"{method} /api/v1/second",
        f"{method} /api/v1/second",
    ]
    assert owner.dropped == [f"{method} /api/v1/second"]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "PATCH"])
async def test_non_idempotent_call_on_a_stale_connection_is_not_sent_again(method: str) -> None:
    with stale_connection_owner() as owner:
        client = ServiceClient("game_session", owner.base_url, CREDENTIAL)
        try:
            await client.send(method, "/api/v1/first", json={}, authorization=None, timeout_s=5.0)
            with pytest.raises(UpstreamUnavailableError) as raised:
                await client.send(
                    method, "/api/v1/second", json={}, authorization=None, timeout_s=5.0
                )
        finally:
            await client.aclose()

    assert raised.value.service == "game_session"
    assert raised.value.reason == "RemoteProtocolError"
    assert owner.received == [f"{method} /api/v1/first", f"{method} /api/v1/second"]


@pytest.mark.asyncio
async def test_a_retried_call_logs_one_warning_with_the_owner_and_method(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with stale_connection_owner() as owner:
        client = ServiceClient("game_session", owner.base_url, CREDENTIAL)
        try:
            await client.send("GET", "/api/v1/first", authorization=None, timeout_s=5.0)
            with caplog.at_level(logging.WARNING, logger="runefoble.service_client"):
                await client.send("GET", "/api/v1/second", authorization=None, timeout_s=5.0)
        finally:
            await client.aclose()

    warnings = [r for r in caplog.records if r.name == "runefoble.service_client"]
    assert len(warnings) == 1
    assert "game_session" in warnings[0].getMessage()
    assert "GET" in warnings[0].getMessage()


@pytest.mark.asyncio
async def test_a_down_owner_still_fails_within_the_connect_limit_for_a_get() -> None:
    """A connect failure is an outage, not a stale connection: the GET is not sent again."""
    with unanswered_port_url() as base_url:
        client = ServiceClient("game_session", base_url, CREDENTIAL)
        started = time.monotonic()
        try:
            with pytest.raises(UpstreamUnavailableError) as raised:
                await client.send("GET", "/api/v1/x", authorization=None, timeout_s=10.0)
            elapsed = time.monotonic() - started
        finally:
            await client.aclose()

    assert raised.value.reason == "ConnectTimeout"
    assert elapsed < 3.0
