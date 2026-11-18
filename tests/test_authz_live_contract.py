"""Live SpiceDB name contract: a real server enforces the schema names the mock enforces.

Run with `make test-authz-live`. The suite needs Docker. Without the live flag it skips.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

import pytest
from runefoble_auth.errors import AuthzSchemaError

pytestmark = pytest.mark.authz_live


@pytest.mark.asyncio
async def test_permission_name_written_as_relation_is_rejected(live_spicedb_with_schema) -> None:
    client = live_spicedb_with_schema.client
    with pytest.raises(AuthzSchemaError):
        await client.write_relationship("campaign", "c1", "play", "user", "u1")


@pytest.mark.asyncio
async def test_game_master_relation_grants_run_session(live_spicedb_with_schema) -> None:
    client = live_spicedb_with_schema.client
    await client.write_relationship("campaign", "c1", "game_master", "user", "u1")
    assert await client.check_permission("campaign", "c1", "run_session", "user", "u1") is True


@pytest.mark.asyncio
async def test_undefined_permission_check_raises_schema_error(live_spicedb_with_schema) -> None:
    client = live_spicedb_with_schema.client
    with pytest.raises(AuthzSchemaError):
        await client.check_permission("campaign", "c1", "teleport", "user", "u1")
