"""Tests for SpiceDB Zanzibar schema bootstrapping, validation, and fallback mechanisms.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
"""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client
from gateway_api.main import app
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
            use_mock=False,
        )
        applied_live = await bootstrap_schema(client=live_client)
        assert "definition board_token" in applied_live


@pytest.mark.asyncio
async def test_spicedb_resilient_fallback_on_unreachable_endpoint() -> None:
    """Verify SpiceDBClient falls back gracefully to in-memory mock when endpoint is unreachable."""
    unreachable_client = SpiceDBClient(
        endpoint="localhost:59997",
        token="invalid_token",
        use_mock=False,
    )
    set_spicedb_client(unreachable_client)
    tc = TestClient(app)

    camp_id = f"camp-fallback-{uuid4().hex[:8]}"
    user_id = "user_fallback"

    # Assign role -> handles gRPC connection failure and writes to mock fallback
    res = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_id, "role": "player"},
    )
    assert res.status_code == 200

    # View session -> evaluates against mock fallback
    res_view = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_id})
    assert res_view.status_code == 200

    # Read relationships from mock fallback
    rels = await unreachable_client.read_relationships(
        resource_type="campaign", resource_id=camp_id
    )
    assert any(r.subject_id == user_id for r in rels)
