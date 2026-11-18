"""Live SpiceDB frontdoor tests for TASK-0808: MCP read tools authorize the caller.

`get_character_sheet` and `inspect_inventory` read a character by id. The gateway checks
`character.view` for the verified MCP caller before it calls character_sheet, and it forwards
the caller bearer, so character_sheet checks the same permission. These tests run both
services against a real SpiceDB container with `runefoble.zed` loaded. Run with
`make test-authz-live` (needs Docker).

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
- ADR-0015: Audit Remediation Decisions (c, e)
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from character_sheet import dependencies as sheet_deps
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from gateway_mcp.dynamic import auth as mcp_auth
from gateway_mcp.server import mcp
from mcp.types import CallToolResult

from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = [pytest.mark.authz_live, pytest.mark.usefixtures("trusted_ws_issuer")]

OWNER = "live-sheet-owner"
STRANGER = "live-sheet-stranger"


@pytest.fixture
def live_read_stack(live_spicedb_with_schema) -> Iterator[str]:
    """Run the MCP gateway and character_sheet on the live SpiceDB client. Yield the MCP URL."""
    live_client = live_spicedb_with_schema.client
    sheet_deps.set_spicedb_client(live_client)
    mcp_auth.set_spicedb_client(live_client)
    try:
        with serve_mcp(mcp) as endpoint:
            yield endpoint
    finally:
        sheet_deps.set_spicedb_client(None)
        mcp_auth.set_spicedb_client(None)


@pytest.fixture
def owned_character(live_read_stack: str) -> str:
    """Create a character as OWNER through the public character_sheet route. Return its id."""
    client = TestClient(character_app)
    res = client.post(
        "/api/v1/characters",
        json={"name": "Live Kyra", "character_class": "Cleric", "max_hp": 30},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(OWNER)}"},
    )
    assert res.status_code == 200, res.text
    return str(res.json()["character_id"])


async def _call(endpoint: str, sub: str, name: str, arguments: dict[str, Any]) -> CallToolResult:
    return await call_tool_over_http(endpoint, name, arguments, SIGNING_ISSUER.mint(sub))


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["get_character_sheet", "inspect_inventory"])
async def test_live_owner_reads_the_sheet_and_stranger_is_refused(
    live_read_stack: str, owned_character: str, tool: str
):
    """On live SpiceDB, the owner reads the character and a stranger gets a tool error."""
    arguments = {"character_id": owned_character}

    owner_result = await _call(live_read_stack, OWNER, tool, arguments)
    stranger_result = await _call(live_read_stack, STRANGER, tool, arguments)

    assert owner_result.isError is False
    assert stranger_result.isError is True
    assert "Live Kyra" not in str(stranger_result.content[0].text)
