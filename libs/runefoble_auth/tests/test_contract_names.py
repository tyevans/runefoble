"""Name contract tests: every action maps to a schema permission, and the strict mock enforces it.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

import pytest
from runefoble_auth.contract import ACTION_PERMISSIONS, load_contract, permission_for_action
from runefoble_auth.errors import AuthzSchemaError, SchemaContractError
from runefoble_auth.mock import MockSpiceDBClient


@pytest.mark.parametrize(("action", "pair"), sorted(ACTION_PERMISSIONS.items()))
def test_every_action_permission_resolves_in_schema(action: str, pair: tuple[str, str]) -> None:
    resource_type, permission = pair
    graph = load_contract()
    assert permission in graph.definitions[resource_type].permissions, action
    assert permission_for_action(action) == pair


def test_unknown_action_is_rejected() -> None:
    with pytest.raises(SchemaContractError):
        permission_for_action("campaign.teleport")


def test_contract_errors_are_schema_errors() -> None:
    assert issubclass(SchemaContractError, AuthzSchemaError)


@pytest.mark.asyncio
async def test_strict_mock_rejects_permission_name_as_relation_write() -> None:
    client = MockSpiceDBClient()
    with pytest.raises(SchemaContractError):
        await client.write_relationship("campaign", "c1", "play", "user", "u1")


@pytest.mark.asyncio
async def test_strict_mock_rejects_role_name_as_relation_write() -> None:
    client = MockSpiceDBClient()
    with pytest.raises(SchemaContractError):
        await client.write_relationship("campaign", "c1", "gm", "user", "u1")


@pytest.mark.asyncio
async def test_strict_mock_accepts_owner_and_game_master_writes() -> None:
    client = MockSpiceDBClient()
    await client.write_relationship("campaign", "c1", "owner", "user", "u1")
    await client.write_relationship("campaign", "c1", "game_master", "user", "u2")
    assert await client.check_permission("campaign", "c1", "manage", "user", "u1")
    assert await client.check_permission("campaign", "c1", "run_session", "user", "u2")


@pytest.mark.asyncio
async def test_strict_mock_rejects_undefined_type_and_subject() -> None:
    client = MockSpiceDBClient()
    with pytest.raises(SchemaContractError):
        await client.write_relationship("system", "s1", "admin", "user", "u1")
    with pytest.raises(SchemaContractError):
        await client.write_relationship("campaign", "c1", "owner", "robot", "r1")


@pytest.mark.asyncio
async def test_strict_mock_rejects_check_of_undefined_permission() -> None:
    client = MockSpiceDBClient()
    with pytest.raises(SchemaContractError):
        await client.check_permission("campaign", "c1", "teleport", "user", "u1")


@pytest.mark.asyncio
async def test_strict_mock_has_no_role_name_grants() -> None:
    client = MockSpiceDBClient()
    await client.write_relationship("campaign", "c1", "owner", "user", "u1")
    # A player relation alone does not grant the DM permission named by a role.
    await client.write_relationship("campaign", "c1", "player", "user", "u2")
    assert not await client.check_permission("campaign", "c1", "manage", "user", "u2")
    assert not await client.check_permission("campaign", "c1", "run_session", "user", "u2")
