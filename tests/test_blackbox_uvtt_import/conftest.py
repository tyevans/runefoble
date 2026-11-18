"""Shared fixtures for Universal VTT import and Dynamic FastMCP test suites."""

from __future__ import annotations

import base64
from collections.abc import Iterator

import httpx
import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_mcp.dynamic import dynamic_registry
from gateway_mcp.server import mcp

from tests.helpers.mcp_http import serve_mcp
from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES
from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))


@pytest.fixture(scope="module")
def mcp_endpoint() -> Iterator[str]:
    """Serve the gateway MCP server over HTTP. The endpoint trusts the shared signing issuer."""
    with serve_mcp(mcp) as endpoint:
        yield endpoint


@pytest.fixture
def tools_client(mcp_endpoint: str) -> Iterator[httpx.Client]:
    """Tool admin client for the MCP process. It sends a signed token for `user-test`."""
    with httpx.Client(
        base_url=mcp_endpoint.removesuffix("/mcp"), headers=bearer("user-test")
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage and dynamic registry for each test."""
    for step in range(2):
        for t in list(dynamic_registry.list_tools()):
            dynamic_registry.deregister_tool(t.name)
        if step == 0:
            yield


def build_sample_dd2vtt_dict(
    cols: int = 16, rows: int = 12, pixels_per_grid: int = 70, include_image: bool = True
) -> dict:
    """Build a canonical Universal VTT (.dd2vtt) dictionary."""
    b64_img = base64.b64encode(PNG_SAMPLE_BYTES).decode("utf-8") if include_image else ""
    origin, size = {"x": 0, "y": 0}, {"x": cols, "y": rows}
    res = {"map_origin": origin, "map_size": size, "pixels_per_grid": pixels_per_grid}
    p1, p2, p3 = {"x": 1.0, "y": 1.0}, {"x": 6.0, "y": 1.0}, {"x": 6.0, "y": 5.0}
    los = [[p1, p2], [p2, p3], [p3, {"x": 1.0, "y": 5.0}]]
    portal = {
        "position": {"x": 3.5, "y": 1.0},
        "bounds": [{"x": 3.0, "y": 1.0}, {"x": 4.0, "y": 1.0}],
        "rotation": 0.0,
        "closed": True,
        "freestanding": False,
    }
    light = {
        "position": {"x": 4.0, "y": 3.0},
        "range": 5.5,
        "intensity": 0.85,
        "color": "ffffc0a0",
        "shadows": True,
    }
    return {
        "format": 0.2,
        "resolution": res,
        "line_of_sight": los,
        "portals": [portal],
        "lights": [light],
        "image": b64_img,
    }
