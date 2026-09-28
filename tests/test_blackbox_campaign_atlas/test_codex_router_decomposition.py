"""Blackbox tests verifying modular APIRouter decomposition for campaign_lore codex.

Governed by:
- ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 500 lines, all submodules < 120 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- TASK-0198: Campaign Lore Codex Router Modular Decomposition
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from campaign_lore.dependencies import get_retrieval_engine
from campaign_lore.main import app as lore_app
from campaign_lore.routers.codex import (
    CrossReferenceContentRequest,
    CrossReferenceResponse,
    PublishCodexEntryRequest,
    UpdateCodexEntryRequest,
    entries_router,
    extract_references,
    format_codex_entry,
    get_entry,
    get_entry_references,
    list_entries,
    publish_entry,
    referencing_router,
    router,
    update_entry,
)
from fastapi import APIRouter
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_codex_modular_file_budgets() -> None:
    """Verify file length limits strictly conform to TASK-0198 DoD and Hard Invariant 6."""
    routers_dir = REPO_ROOT / "services" / "campaign_lore" / "src" / "campaign_lore" / "routers"
    codex_pkg_dir = routers_dir / "codex"
    codex_facade = routers_dir / "codex.py"

    assert codex_facade.exists(), "codex.py aggregator facade must exist"
    assert codex_pkg_dir.is_dir(), "codex/ router package directory must exist"

    facade_lines = len(codex_facade.read_text(encoding="utf-8").splitlines())
    init_lines = len((codex_pkg_dir / "__init__.py").read_text(encoding="utf-8").splitlines())
    schemas_lines = len((codex_pkg_dir / "schemas.py").read_text(encoding="utf-8").splitlines())
    entries_lines = len((codex_pkg_dir / "entries.py").read_text(encoding="utf-8").splitlines())
    referencing_lines = len(
        (codex_pkg_dir / "referencing.py").read_text(encoding="utf-8").splitlines()
    )

    # TASK-0198 Specification Limits:
    assert facade_lines < 50, f"codex.py facade exceeds 50 lines ({facade_lines} lines)"
    assert init_lines < 50, f"codex/__init__.py exceeds 50 lines ({init_lines} lines)"
    assert schemas_lines < 80, f"codex/schemas.py exceeds 80 lines ({schemas_lines} lines)"
    assert entries_lines < 110, f"codex/entries.py exceeds 110 lines ({entries_lines} lines)"
    assert referencing_lines < 100, (
        f"codex/referencing.py exceeds 100 lines ({referencing_lines} lines)"
    )

    # Hard Invariant 6: All submodules strictly < 120 lines
    for py_file in codex_pkg_dir.glob("*.py"):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        assert line_count < 120, f"{py_file.name} violates < 120 lines limit ({line_count} lines)"

    # Hard Invariant 6: All files in campaign_lore router directory strictly < 500 lines
    for py_file in routers_dir.glob("*.py"):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"{py_file.name} violates Hard Invariant 6 ({line_count} lines)"


def test_codex_facade_and_symbol_reexports() -> None:
    """Verify facade and package re-export APIRouter and symbols for 100% backward compatibility."""
    assert isinstance(router, APIRouter)
    assert isinstance(entries_router, APIRouter)
    assert isinstance(referencing_router, APIRouter)

    for fn in [
        publish_entry,
        list_entries,
        get_entry,
        update_entry,
        get_entry_references,
        extract_references,
    ]:
        assert callable(fn), f"Expected callable endpoint function: {fn}"

    for model in [
        PublishCodexEntryRequest,
        UpdateCodexEntryRequest,
        CrossReferenceContentRequest,
        CrossReferenceResponse,
    ]:
        assert issubclass(model, object)
    assert callable(format_codex_entry)


def test_codex_openapi_routes_completeness() -> None:
    """Verify all decomposed codex routes are mounted in lore_app OpenAPI schema."""
    paths = lore_app.openapi()["paths"]
    expected_routes = [
        "/api/v1/campaigns/{campaign_id}/codex/entries",
        "/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        "/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}/references",
        "/api/v1/campaigns/{campaign_id}/codex/references/extract",
    ]
    for route in expected_routes:
        assert route in paths, f"Route '{route}' missing from Campaign Lore OpenAPI schema"


@pytest.mark.asyncio
async def test_codex_frontdoor_referencing_and_crud(
    client: TestClient, spicedb: SpiceDBClient, campaign_id: str
) -> None:
    """Verify frontdoor publishing, referencing extraction, filtering, and Zanzibar privacy."""
    dm_user, player_user = f"dm_{uuid4().hex[:6]}", f"player_{uuid4().hex[:6]}"
    dm_h, player_h = {"x-user-id": dm_user}, {"x-user-id": player_user}
    base = f"/api/v1/campaigns/{campaign_id}/codex"

    # Set up Zanzibar permissions for campaign
    await spicedb.write_relationship("campaign", campaign_id, "run_session", "user", dm_user)
    await spicedb.write_relationship("campaign", campaign_id, "play", "user", player_user)
    await spicedb.write_relationship("campaign", campaign_id, "view", "user", player_user)

    # Ingest document to populate redstring entity graph
    await get_retrieval_engine().ingest_document(
        uuid4(),
        UUID(campaign_id),
        "Keep of the Silver Gryphon",
        "The Silver Gryphon is an ancient bastion guarded by Lord Theresa.",
    )

    # 1. Test standalone reference extraction frontdoor
    ext_resp = client.post(
        f"{base}/references/extract",
        json={"content": "We travel to the Silver Gryphon to meet Lord Theresa."},
        headers=dm_h,
    )
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert any("Silver Gryphon" in e["name"] for e in ext_data["linked_entities"])
    assert "Silver Gryphon](#lore/entity/" in ext_data["illuminated_content"]

    # 2. Publish private codex note by DM
    pub_resp = client.post(
        f"{base}/entries",
        json={
            "title": "Gryphon Reconnaissance",
            "content": "Secret reports near Silver Gryphon.",
            "privacy": "private",
            "era": "Age of Valor",
            "tags": ["secret", "recon"],
        },
        headers=dm_h,
    )
    assert pub_resp.status_code == 201
    entry_id = pub_resp.json()["entry_id"]
    entry_url = f"{base}/entries/{entry_id}"
    assert pub_resp.json()["privacy"] == "private"
    assert pub_resp.json()["status"] == "published"

    # 3. Dedicated reference retrieval endpoint
    ref_resp = client.get(f"{entry_url}/references", headers=dm_h)
    assert ref_resp.status_code == 200
    ref_data = ref_resp.json()
    assert ref_data["entry_id"] == entry_id
    assert any("Silver Gryphon" in e["name"] for e in ref_data["linked_entities"])

    # 4. Zanzibar access check on private entry: DM allowed, player forbidden
    assert client.get(entry_url, headers=dm_h).status_code == 200
    assert client.get(entry_url, headers=player_h).status_code == 403
    assert client.get(f"{entry_url}/references", headers=player_h).status_code == 403

    # 5. List entries with search and era filter
    dm_list = client.get(f"{base}/entries?search=Reconnaissance&era=valor", headers=dm_h)
    assert dm_list.status_code == 200
    assert entry_id in [e["entry_id"] for e in dm_list.json()]

    # Player list excludes private note
    player_list = client.get(f"{base}/entries", headers=player_h)
    assert player_list.status_code == 200
    assert entry_id not in [e["entry_id"] for e in player_list.json()]

    # 6. Update entry to party_shared and verify player can now access
    patch_resp = client.patch(
        entry_url,
        json={"privacy": "party_shared", "title": "Shared Gryphon Recon"},
        headers=dm_h,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "updated"
    assert patch_resp.json()["privacy"] == "party_shared"

    assert client.get(entry_url, headers=player_h).status_code == 200
    assert client.get(f"{entry_url}/references", headers=player_h).status_code == 200
    player_list_after = client.get(f"{base}/entries", headers=player_h)
    assert entry_id in [e["entry_id"] for e in player_list_after.json()]
