"""Tests for SpiceDB Zanzibar schema bootstrapping, validation, and fallback mechanisms.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
"""

from pathlib import Path

import grpc
import pytest
from runefoble_auth.bootstrap_schema import DEFAULT_SCHEMA_PATH, bootstrap_schema
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient


def test_schema_file_exists_and_syntax_structure() -> None:
    """Verify runefoble.zed exists, is non-empty, and contains core Zanzibar definitions."""
    assert DEFAULT_SCHEMA_PATH.is_file(), f"Schema file missing at {DEFAULT_SCHEMA_PATH}"
    schema_text = DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")
    assert schema_text.strip(), "Schema file cannot be empty"

    expected_definitions = [
        "definition user",
        "definition campaign",
        "definition character",
        "definition session",
        "definition game_session",
        "definition board_token",
        "definition lore_document",
        "definition homebrew_rule",
        "definition forged_asset",
        "definition audience_poll",
    ]
    for d in expected_definitions:
        assert d in schema_text, f"Missing definition: {d}"

    assert "relation dungeon_master: user" in schema_text
    assert "permission run_session = owner + dungeon_master + game_master" in schema_text


@pytest.mark.asyncio
async def test_bootstrap_schema_empty_file_validation(tmp_path: Path) -> None:
    """Verify bootstrap_schema raises ValueError on empty schema file."""
    empty_file = tmp_path / "empty.zed"
    empty_file.write_text("")
    with pytest.raises(ValueError, match="is empty"):
        await bootstrap_schema(schema_path=empty_file)


@pytest.mark.asyncio
async def test_schema_bootstrapper_execution(live_spicedb_endpoint: str | None) -> None:
    """Verify schema bootstrapper applies schema from file to mock and live clients."""
    mock_client = MockSpiceDBClient()
    applied = await bootstrap_schema(client=mock_client)
    assert "definition campaign" in applied
    assert await mock_client.read_schema() == applied

    if live_spicedb_endpoint:
        live_client = SpiceDBClient(
            endpoint=live_spicedb_endpoint,
            token="bootstrap_test_token",
        )
        applied_live = await bootstrap_schema(client=live_client)
        assert "definition board_token" in applied_live


@pytest.mark.asyncio
async def test_spicedb_client_fails_on_unreachable_endpoint() -> None:
    """Verify SpiceDBClient raises an error when endpoint is unreachable without falling back to mock."""
    unreachable_client = SpiceDBClient(
        endpoint="localhost:59997",
        token="invalid_token",
    )
    with pytest.raises(grpc.RpcError):
        await unreachable_client.write_relationship(
            resource_type="campaign",
            resource_id="camp-1",
            relation="player",
            subject_type="user",
            subject_id="u-1",
        )
