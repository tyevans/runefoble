"""Blackbox tests for how MCP tools call owning services (TASK-0745).

An MCP tool call reaches the owning service through the shared service client. Each upstream
call carries the service credential (ADR-0015 e) and the W3C trace context. An agent-supplied
path segment stays inside one path segment. The upstream is a loopback stand-in that records
what it receives. Nothing patches the HTTP client.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gateway_mcp.server import mcp
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from runefoble_platform.config import PlatformSettings
from runefoble_platform.telemetry import init_telemetry, reset_tracer_provider

from tests.helpers.live_services import serve
from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.ws_identity import SIGNING_ISSUER


def _record(request: Request) -> dict[str, Any]:
    """Return what the upstream received: the raw path and the gateway headers."""
    return {
        "raw_path": request.scope["raw_path"].decode(),
        "service_credential": request.headers.get("x-runefoble-service-credential"),
        "traceparent": request.headers.get("traceparent"),
    }


def _recording_board_app(received: list[dict[str, Any]]) -> FastAPI:
    """Return a board_state stand-in. Only the board route exists. Every other route is a 404."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    def _board(session_id: str, request: Request) -> dict[str, Any]:
        received.append(_record(request))
        return {
            "session_id": session_id,
            "cols": 10,
            "rows": 8,
            "tokens": {},
            "active_hazards": [],
        }

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    def _other(path: str, request: Request) -> JSONResponse:
        received.append(_record(request))
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    return app


@pytest.fixture
def board_upstream(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """Point the gateway at a recording board_state stand-in and yield what it receives."""
    received: list[dict[str, Any]] = []
    with serve(_recording_board_app(received)) as board_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        yield received


@pytest.fixture
def span_exporter() -> Iterator[InMemorySpanExporter]:
    """Install a tracer provider for this test, so tool calls have an active trace context."""
    exporter = InMemorySpanExporter()
    init_telemetry(
        service_name="gateway-mcp",
        settings=PlatformSettings(environment="test"),
        span_exporter=exporter,
        force=True,
    )
    yield exporter
    reset_tracer_provider()


@pytest.fixture(scope="module")
def mcp_endpoint() -> Iterator[str]:
    """Serve the gateway MCP server over streamable HTTP for this module."""
    with serve_mcp(mcp) as endpoint:
        yield endpoint


@pytest.mark.asyncio
async def test_tool_call_sends_service_credential_and_traceparent_upstream(
    mcp_endpoint: str, board_upstream: list[dict[str, Any]], span_exporter: InMemorySpanExporter
):
    """Every upstream call from a tool carries the service credential and a traceparent."""
    result = await call_tool_over_http(
        mcp_endpoint,
        "inspect_tactical_board",
        {"session_id": "camp-7"},
        SIGNING_ISSUER.mint("user-test"),
    )

    assert result.isError is False
    assert len(board_upstream) == 1
    upstream_call = board_upstream[0]
    assert upstream_call["raw_path"] == "/api/v1/boards/camp-7"
    assert upstream_call["service_credential"] == os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]
    assert upstream_call["traceparent"] is not None
    assert upstream_call["traceparent"].startswith("00-")


@pytest.mark.asyncio
async def test_session_id_with_separators_stays_in_one_path_segment(
    mcp_endpoint: str, board_upstream: list[dict[str, Any]]
):
    """An agent session id with '/', '?' and '#' reaches no other route. The tool returns an error."""
    result = await call_tool_over_http(
        mcp_endpoint,
        "inspect_tactical_board",
        {"session_id": "camp/7?x#y"},
        SIGNING_ISSUER.mint("user-test"),
    )

    assert result.isError is True
    assert [call["raw_path"] for call in board_upstream] == ["/api/v1/boards/camp%2F7%3Fx%23y"]
