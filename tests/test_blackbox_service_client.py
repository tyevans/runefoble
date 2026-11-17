"""Blackbox tests for the shared typed service client (TASK-0580).

The client is driven through its public constructor and `send` method. The owning
service is a stand-in on a loopback port (ADR-0014), so the real HTTP path runs.
Nothing patches the HTTP client.

Governed by:
- TASK-0580: Shared Typed Service Client for Gateway Proxies
- ADR-0015 decision (b): one shared typed client, no substitute values
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from runefoble_platform.service_client import (
    ServiceClient,
    UpstreamFailureError,
    UpstreamUnavailableError,
)

from tests.helpers.live_services import closed_port_url, serve

pytestmark = pytest.mark.asyncio


def _recording_upstream(seen: list[dict[str, Any]]) -> FastAPI:
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def _record(request: Request) -> JSONResponse:
        seen.append(dict(request.headers))
        if request.url.path.endswith("/missing"):
            return JSONResponse({"error": "no such pin"}, status_code=404)
        if request.url.path.endswith("/broken"):
            return JSONResponse({"error": "boom"}, status_code=500)
        if request.url.path.endswith("/slow"):
            await asyncio.sleep(1.0)
        return JSONResponse({"ok": True})

    return app


async def test_client_returns_upstream_4xx_as_a_reply() -> None:
    """A 404 from the owning service is returned unchanged, not raised."""
    seen: list[dict[str, Any]] = []
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("campaign_lore", base_url)
        try:
            reply = await client.send(
                "GET", "/api/v1/pins/missing", authorization=None, timeout_s=5.0
            )
        finally:
            await client.aclose()

    assert reply.status_code == 404
    assert reply.content_type.startswith("application/json")
    assert reply.body == b'{"error":"no such pin"}'


async def test_client_raises_failure_on_upstream_5xx() -> None:
    """An upstream 500 raises UpstreamFailureError with the service name and status."""
    seen: list[dict[str, Any]] = []
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("campaign_lore", base_url)
        try:
            with pytest.raises(UpstreamFailureError) as raised:
                await client.send("GET", "/api/v1/broken", authorization=None, timeout_s=5.0)
        finally:
            await client.aclose()

    assert raised.value.service == "campaign_lore"
    assert raised.value.status_code == 500


async def test_client_raises_unavailable_on_connect_failure() -> None:
    """A refused connection raises UpstreamUnavailableError with the service name."""
    client = ServiceClient("soundscape", closed_port_url())
    try:
        with pytest.raises(UpstreamUnavailableError) as raised:
            await client.send("GET", "/api/v1/x", authorization=None, timeout_s=2.0)
    finally:
        await client.aclose()

    assert raised.value.service == "soundscape"


async def test_client_times_out_at_the_caller_timeout() -> None:
    """A slow owning service fails at the per-call timeout, not at a default."""
    seen: list[dict[str, Any]] = []
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("soundscape", base_url)
        started = time.monotonic()
        try:
            with pytest.raises(UpstreamUnavailableError):
                await client.send("GET", "/api/v1/slow", authorization=None, timeout_s=0.2)
            elapsed = time.monotonic() - started
        finally:
            await client.aclose()

    assert elapsed < 0.9


async def test_client_forwards_only_the_authorization_and_trace_headers() -> None:
    """The upstream sees the bearer value and the active traceparent, and no other header."""
    seen: list[dict[str, Any]] = []
    tracer = TracerProvider().get_tracer("service-client-test")
    span = tracer.start_span("gateway-to-lore")
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("campaign_lore", base_url)
        try:
            with trace.use_span(span, end_on_exit=True):
                await client.send(
                    "GET",
                    "/api/v1/pins",
                    authorization="Bearer token-value",
                    timeout_s=5.0,
                )
        finally:
            await client.aclose()

    received = seen[-1]
    assert received["authorization"] == "Bearer token-value"
    assert received["traceparent"].startswith("00-")
    assert "x-forwarded-foo" not in received
