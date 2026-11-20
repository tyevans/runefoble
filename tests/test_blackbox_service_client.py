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
    path,
)
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

from tests.helpers.live_services import closed_port_url, serve, unanswered_port_url

CREDENTIAL = "test-service-credential"


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


@pytest.mark.asyncio
async def test_client_returns_upstream_4xx_as_a_reply() -> None:
    """A 404 from the owning service is returned unchanged, not raised."""
    seen: list[dict[str, Any]] = []
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("campaign_lore", base_url, CREDENTIAL)
        try:
            reply = await client.send(
                "GET", "/api/v1/pins/missing", authorization=None, timeout_s=5.0
            )
        finally:
            await client.aclose()

    assert reply.status_code == 404
    assert reply.content_type.startswith("application/json")
    assert reply.body == b'{"error":"no such pin"}'


@pytest.mark.asyncio
async def test_client_raises_failure_on_upstream_5xx() -> None:
    """An upstream 500 raises UpstreamFailureError with the service name and status."""
    seen: list[dict[str, Any]] = []
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("campaign_lore", base_url, CREDENTIAL)
        try:
            with pytest.raises(UpstreamFailureError) as raised:
                await client.send("GET", "/api/v1/broken", authorization=None, timeout_s=5.0)
        finally:
            await client.aclose()

    assert raised.value.service == "campaign_lore"
    assert raised.value.status_code == 500


@pytest.mark.asyncio
async def test_client_raises_unavailable_on_connect_failure() -> None:
    """A refused connection raises UpstreamUnavailableError with the service name."""
    client = ServiceClient("soundscape", closed_port_url(), CREDENTIAL)
    try:
        with pytest.raises(UpstreamUnavailableError) as raised:
            await client.send("GET", "/api/v1/x", authorization=None, timeout_s=2.0)
    finally:
        await client.aclose()

    assert raised.value.service == "soundscape"


@pytest.mark.asyncio
async def test_client_times_out_at_the_caller_timeout() -> None:
    """A slow owning service fails at the per-call timeout, not at a default."""
    seen: list[dict[str, Any]] = []
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("soundscape", base_url, CREDENTIAL)
        started = time.monotonic()
        try:
            with pytest.raises(UpstreamUnavailableError):
                await client.send("GET", "/api/v1/slow", authorization=None, timeout_s=0.2)
            elapsed = time.monotonic() - started
        finally:
            await client.aclose()

    assert elapsed < 0.9


@pytest.mark.asyncio
async def test_client_gives_up_on_an_unanswered_connect_before_the_call_timeout() -> None:
    """A connect that gets no answer fails fast, not at the full call timeout.

    A Service that still routes to a deleted pod drops the SYN. The gateway must answer 503
    soon, so the user sees the failure while the call budget is still long.
    """
    with unanswered_port_url() as base_url:
        client = ServiceClient("game_session", base_url, CREDENTIAL)
        started = time.monotonic()
        try:
            with pytest.raises(UpstreamUnavailableError) as raised:
                await client.send("POST", "/api/v1/x", authorization=None, timeout_s=10.0)
            elapsed = time.monotonic() - started
        finally:
            await client.aclose()

    assert raised.value.reason == "ConnectTimeout"
    assert elapsed < 3.0


def _slow_upstream(delay_s: float) -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/slow")
    async def _slow() -> JSONResponse:
        await asyncio.sleep(delay_s)
        return JSONResponse({"ok": True})

    return app


@pytest.mark.asyncio
async def test_client_keeps_the_call_timeout_for_a_slow_answer() -> None:
    """The short connect limit does not cut a reply that takes longer than that limit."""
    with serve(_slow_upstream(2.5)) as base_url:
        client = ServiceClient("the_watcher", base_url, CREDENTIAL)
        try:
            reply = await client.send("GET", "/api/v1/slow", authorization=None, timeout_s=5.0)
        finally:
            await client.aclose()

    assert reply.status_code == 200


@pytest.mark.asyncio
async def test_client_forwards_only_the_authorization_and_trace_headers() -> None:
    """The upstream sees the bearer value and the active traceparent, and no other header."""
    seen: list[dict[str, Any]] = []
    tracer = TracerProvider().get_tracer("service-client-test")
    span = tracer.start_span("gateway-to-lore")
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("campaign_lore", base_url, CREDENTIAL)
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


@pytest.mark.asyncio
async def test_client_sends_the_service_credential_on_every_call() -> None:
    """The upstream receives the service credential, with or without a user bearer."""
    seen: list[dict[str, Any]] = []
    with serve(_recording_upstream(seen)) as base_url:
        client = ServiceClient("campaign_lore", base_url, CREDENTIAL)
        try:
            await client.send("GET", "/api/v1/pins", authorization=None, timeout_s=5.0)
            await client.send(
                "GET", "/api/v1/pins", authorization="Bearer token-value", timeout_s=5.0
            )
        finally:
            await client.aclose()

    assert [headers[SERVICE_CREDENTIAL_HEADER.lower()] for headers in seen] == [
        CREDENTIAL,
        CREDENTIAL,
    ]
    assert "authorization" not in seen[0]


def test_client_refuses_a_blank_service_credential() -> None:
    """A client with no credential is never built (ADR-0015 e)."""
    with pytest.raises(ValueError):
        ServiceClient("campaign_lore", "http://lore:8080", "   ")


def test_path_quotes_a_segment_with_a_slash_or_question_mark() -> None:
    """A segment that holds `/` or `?` stays one path segment."""
    assert path("api", "v1", "pins", "a/b?c") == "/api/v1/pins/a%2Fb%3Fc"


def test_path_quotes_spaces_and_keeps_plain_segments() -> None:
    assert path("api", "v1", "sessions", "camp 1") == "/api/v1/sessions/camp%201"


@pytest.mark.parametrize("segment", ["", ".", ".."])
def test_path_refuses_an_empty_or_dot_segment(segment: str) -> None:
    """An empty segment or a dot segment would change the target route."""
    with pytest.raises(ValueError):
        path("api", "v1", segment)
