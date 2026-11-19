"""Blackbox tests: a declarative handler runs in bounded time and gives a finite result (TASK-0737).

ADR-0020 removed user code, so no handler can loop. These tests close the remaining ways
in which a valid expression could take a long time or give a result that JSON cannot carry.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.helpers.mcp_http import call_tool_over_http
from tests.helpers.ws_identity import SIGNING_ISSUER

PARAMS = {
    "type": "object",
    "properties": {
        "base": {"type": "integer"},
        "ratio": {"type": "number"},
        "digits": {"type": "integer"},
    },
    "required": ["base"],
}


def _register(client: TestClient, name: str, handler: object):
    return client.post(
        "/mcp/tools/register", json={"name": name, "parameters": PARAMS, "handler": handler}
    )


def _execute(client: TestClient, name: str, arguments: dict):
    return client.post(f"/mcp/tools/{name}/execute", json={"arguments": arguments})


def test_registration_refuses_round_with_huge_constant_digits(client: TestClient):
    res = _register(client, "huge_round", {"x": {"$expr": "round(base, -1000000000)"}})

    assert res.status_code == 400
    assert "round" in res.json()["detail"]
    assert client.get("/mcp/tools/huge_round").status_code == 404


def test_round_with_huge_argument_digits_fails_fast_with_400(client: TestClient):
    assert (
        _register(client, "arg_round", {"x": {"$expr": "round(base, digits)"}}).status_code == 200
    )

    started = time.monotonic()
    res = _execute(client, "arg_round", {"base": 5, "digits": -10_000_000})

    assert time.monotonic() - started < 2
    assert res.status_code == 400
    assert "round" in res.json()["detail"]
    assert _execute(client, "arg_round", {"base": 1234, "digits": -2}).json()["result"] == {
        "x": 1200
    }


@pytest.mark.asyncio
async def test_slow_round_over_mcp_is_a_fast_tool_error_and_other_routes_answer(
    client: TestClient, mcp_endpoint: str
):
    """The MCP call and a concurrent admin request both answer within the time bound."""
    assert (
        _register(client, "mcp_round", {"x": {"$expr": "round(base, digits)"}}).status_code == 200
    )
    catalog_url = mcp_endpoint + "/tools/dynamic"
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('user-test')}"}

    started = time.monotonic()
    async with httpx.AsyncClient(headers=headers, timeout=5) as http:
        result, catalog = await asyncio.gather(
            call_tool_over_http(
                mcp_endpoint,
                "mcp_round",
                {"base": 5, "digits": -10_000_000},
                SIGNING_ISSUER.mint("user-test"),
            ),
            http.get(catalog_url),
        )

    assert time.monotonic() - started < 2
    assert result.isError
    assert catalog.status_code == 200


def test_argument_outside_the_number_limit_is_refused(client: TestClient):
    assert _register(client, "square", {"x": {"$expr": "base * base"}}).status_code == 200

    res = _execute(client, "square", {"base": 10**4000})

    assert res.status_code == 400
    assert "base" in res.json()["detail"]


def test_non_finite_float_result_is_refused(client: TestClient):
    handler = {
        "x": {"$expr": "ratio / 0.000000001 / 0.000000001 - ratio / 0.000000001 / 0.000000001"}
    }
    assert _register(client, "overflow", handler).status_code == 200

    res = _execute(client, "overflow", {"base": 1, "ratio": 1e300})

    assert res.status_code == 400
    assert "finite" in res.json()["detail"]
