"""Blackbox tests verifying modular decomposition of campaign_lore dependencies and permissions.

Governed by:
- ADR-0001: Google Zanzibar / SpiceDB Fine-Grained Authorization
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 500 lines, all modular dependencies < 150 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- TASK-0245: Campaign Lore Dependencies and Permissions Modular Decomposition
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from campaign_lore import codex_deps, dependencies, permissions
from campaign_lore.main import app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_dependency_module_file_budgets() -> None:
    """Verify dependencies, permissions, and codex_deps strictly conform to TASK-0245 budgets."""
    pkg_dir = REPO_ROOT / "services" / "campaign_lore" / "src" / "campaign_lore"
    deps_file = pkg_dir / "dependencies.py"
    perm_file = pkg_dir / "permissions.py"
    codex_file = pkg_dir / "codex_deps.py"

    assert deps_file.exists(), "dependencies.py must exist"
    assert perm_file.exists(), "permissions.py must exist"
    assert codex_file.exists(), "codex_deps.py must exist"

    deps_lines = len(deps_file.read_text(encoding="utf-8").splitlines())
    perm_lines = len(perm_file.read_text(encoding="utf-8").splitlines())
    codex_lines = len(codex_file.read_text(encoding="utf-8").splitlines())

    assert deps_lines < 150, f"dependencies.py exceeds 150 lines ({deps_lines} lines)"
    assert deps_lines < 120, f"dependencies.py exceeds target 120 lines ({deps_lines} lines)"

    assert perm_lines < 150, f"permissions.py exceeds 150 lines ({perm_lines} lines)"
    assert perm_lines < 120, f"permissions.py exceeds target 120 lines ({perm_lines} lines)"

    assert codex_lines < 150, f"codex_deps.py exceeds 150 lines ({codex_lines} lines)"


def test_backward_compatibility_reexports() -> None:
    """Verify dependencies.py re-exports modular symbols for 100% backward compatibility."""
    expected_perm_symbols = [
        "check_user_can_read_secrets",
        "check_user_can_view_campaign",
        "check_user_can_interact_handout",
        "check_user_can_inspect_relic",
        "check_user_can_play_campaign",
        "get_current_user_id",
    ]
    for sym in expected_perm_symbols:
        assert hasattr(permissions, sym), f"permissions.{sym} missing"
        assert hasattr(dependencies, sym), f"dependencies.{sym} missing"
        assert getattr(dependencies, sym) is getattr(permissions, sym)

    expected_codex_symbols = [
        "check_user_can_view_codex_entry",
        "check_user_can_edit_codex_entry",
        "require_campaign_view",
        "load_codex_entry",
        "write_codex_permissions",
        "update_codex_permissions",
        "CodexSessionDeps",
    ]
    for sym in expected_codex_symbols:
        assert hasattr(codex_deps, sym), f"codex_deps.{sym} missing"
        assert hasattr(dependencies, sym), f"dependencies.{sym} missing"
        assert getattr(dependencies, sym) is getattr(codex_deps, sym)

    expected_core_getters = [
        "get_repo",
        "get_handout_repo",
        "get_relic_repo",
        "get_retrieval_engine",
        "get_spicedb_client",
        "get_atlas_repo",
        "get_codex_repo",
        "get_codex_referencer",
        "get_campaign_codex_index",
        "get_west_marches_repo",
        "set_west_marches_repo",
        "set_spicedb_client",
    ]
    for getter in expected_core_getters:
        assert hasattr(dependencies, getter), f"dependencies.{getter} missing"
        assert callable(getattr(dependencies, getter))


@pytest.mark.asyncio
async def test_frontdoor_codex_crud_and_permissions() -> None:
    """Verify codex endpoints enforce SpiceDB Zanzibar authorization through public frontdoors."""
    client = TestClient(app)
    spicedb = dependencies.get_spicedb_client()

    campaign_id = str(uuid4())
    author_id = f"user-author-{uuid4()}"
    viewer_id = f"user-viewer-{uuid4()}"
    stranger_id = f"user-stranger-{uuid4()}"

    await spicedb.write_relationship("campaign", campaign_id, "view", "user", author_id)
    await spicedb.write_relationship("campaign", campaign_id, "view", "user", viewer_id)
    await spicedb.write_relationship("campaign", campaign_id, "play", "user", viewer_id)

    # 1. Author publishes a private codex entry
    publish_payload = {
        "title": "Secret Journal of the Void",
        "content": "Deep in the Whispering Fen, the obsidian obelisk hums with ancient power.",
        "category": "lore",
        "privacy": "private",
        "tags": ["ruins", "secret"],
        "era": "Third Age",
    }
    pub_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        json=publish_payload,
        headers={"x-user-id": author_id},
    )
    assert pub_res.status_code == 201, pub_res.text
    entry_data = pub_res.json()
    entry_id = entry_data["entry_id"]
    assert entry_data["title"] == "Secret Journal of the Void"
    assert entry_data["status"] == "published"

    # 2. Author can read and update the private entry
    get_res = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        headers={"x-user-id": author_id},
    )
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Secret Journal of the Void"

    # 3. Non-author viewer cannot read private entry
    viewer_get = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        headers={"x-user-id": viewer_id},
    )
    assert viewer_get.status_code == 403

    # 4. Non-author viewer cannot edit private entry
    viewer_patch = client.patch(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        json={"title": "Hacked Title"},
        headers={"x-user-id": viewer_id},
    )
    assert viewer_patch.status_code == 403

    # 5. Stranger (no campaign permissions) is forbidden from listing or editing
    stranger_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        headers={"x-user-id": stranger_id},
    )
    assert stranger_list.status_code == 403

    stranger_patch = client.patch(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        json={"title": "Stranger Hacked"},
        headers={"x-user-id": stranger_id},
    )
    assert stranger_patch.status_code == 403

    # 6. Author updates entry privacy to party_shared
    author_patch = client.patch(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        json={"privacy": "party_shared", "title": "Revealed Sunken Tower"},
        headers={"x-user-id": author_id},
    )
    assert author_patch.status_code == 200
    assert author_patch.json()["privacy"] == "party_shared"

    # 7. Now viewer (who has campaign play permission) can read the entry
    viewer_shared_get = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        headers={"x-user-id": viewer_id},
    )
    assert viewer_shared_get.status_code == 200
    assert viewer_shared_get.json()["title"] == "Revealed Sunken Tower"


@pytest.mark.asyncio
async def test_frontdoor_permissions_evaluation() -> None:
    """Verify all extracted permission checks evaluate correctly with Zanzibar schema."""
    spicedb = dependencies.get_spicedb_client()
    campaign_id = uuid4()
    cid_str = str(campaign_id)
    dm_user = f"dm-{uuid4()}"
    player_user = f"player-{uuid4()}"
    guest_user = f"guest-{uuid4()}"

    # Setup permissions: DM has run_session, player has play + view, guest has view only
    await spicedb.write_relationship("campaign", cid_str, "run_session", "user", dm_user)
    await spicedb.write_relationship("campaign", cid_str, "play", "user", player_user)
    await spicedb.write_relationship("campaign", cid_str, "view", "user", player_user)
    await spicedb.write_relationship("campaign", cid_str, "view", "user", guest_user)

    # Secrets: only DM can read secrets
    assert await permissions.check_user_can_read_secrets(dm_user, campaign_id, spicedb) is True
    assert await permissions.check_user_can_read_secrets(player_user, campaign_id, spicedb) is False
    assert await permissions.check_user_can_read_secrets(guest_user, campaign_id, spicedb) is False
    assert await permissions.check_user_can_read_secrets(None, campaign_id, spicedb) is False

    # Campaign view
    assert await permissions.check_user_can_view_campaign(dm_user, campaign_id, spicedb) is True
    assert await permissions.check_user_can_view_campaign(guest_user, campaign_id, spicedb) is True

    # Handout interaction (requires play)
    assert (
        await permissions.check_user_can_interact_handout(player_user, campaign_id, spicedb) is True
    )
    assert (
        await permissions.check_user_can_interact_handout(guest_user, campaign_id, spicedb) is False
    )

    # Relic inspection (requires view)
    assert await permissions.check_user_can_inspect_relic(guest_user, campaign_id, spicedb) is True

    # Play campaign (play or run_session)
    assert await permissions.check_user_can_play_campaign(dm_user, campaign_id, spicedb) is True
    assert await permissions.check_user_can_play_campaign(player_user, campaign_id, spicedb) is True
    assert await permissions.check_user_can_play_campaign(guest_user, campaign_id, spicedb) is False
