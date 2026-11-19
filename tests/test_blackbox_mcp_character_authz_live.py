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

import httpx
import pytest
from mcp.types import CallToolResult
from runefoble_auth.factory import get_spicedb_client, set_spicedb_client

from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.module_state import restored_seam
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = [pytest.mark.authz_live, pytest.mark.usefixtures("trusted_ws_issuer")]

OWNER = "live-sheet-owner"
STRANGER = "live-sheet-stranger"


@pytest.fixture
def live_read_stack(live_spicedb_with_schema, character_sheet_upstream) -> Iterator[str]:
    """Run character_sheet as a live upstream and the MCP gateway on the live SpiceDB client.

    Yield the MCP endpoint. The gateway reaches character_sheet over HTTP, and character_sheet
    checks the same live schema, so both checks read the same tuples.
    """
    live_client = live_spicedb_with_schema.client
    with (
        restored_seam(get_spicedb_client, set_spicedb_client, live_client, replace=True),
        serve_mcp() as endpoint,
    ):
        yield endpoint


@pytest.fixture
def owned_character(live_read_stack: str, character_sheet_upstream: str) -> str:
    """Create a character as OWNER through the public character_sheet route. Return its id."""
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(OWNER)}"}
    with httpx.Client(base_url=character_sheet_upstream, headers=headers) as http:
        res = http.post(
            "/api/v1/characters",
            json={"name": "Live Kyra", "character_class": "Cleric", "max_hp": 30},
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
