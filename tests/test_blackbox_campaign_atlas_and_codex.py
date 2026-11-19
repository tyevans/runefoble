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

from uuid import uuid4

import pytest
from campaign_lore import dependencies, permissions
from campaign_lore.main import app
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client

from tests.helpers.ws_identity import bearer

VISITOR_SUBJECT = "lore-test-visitor"


def test_dependencies_expose_core_getters() -> None:
    """Verify dependencies.py exposes its own repository, client and session getters."""
    expected_core_getters = [
        "get_repo",
        "get_handout_repo",
        "get_relic_repo",
        "get_retrieval_engine",
        "get_atlas_repo",
        "get_codex_repo",
        "get_codex_referencer",
        "get_west_marches_repo",
        "set_west_marches_repo",
    ]
    for getter in expected_core_getters:
        assert hasattr(dependencies, getter), f"dependencies.{getter} missing"
        assert callable(getattr(dependencies, getter))


@pytest.mark.asyncio
@pytest.mark.usefixtures("lore_backends")
async def test_frontdoor_codex_crud_and_permissions() -> None:
    """Verify codex endpoints enforce SpiceDB Zanzibar authorization through public frontdoors."""
    with TestClient(app, headers=bearer(VISITOR_SUBJECT)) as client:
        spicedb = get_spicedb_client()

        campaign_id = str(uuid4())
        author_id = f"user-author-{uuid4()}"
        viewer_id = f"user-viewer-{uuid4()}"
        stranger_id = f"user-stranger-{uuid4()}"

        await spicedb.write_relationship("campaign", campaign_id, "player", "user", author_id)
        await spicedb.write_relationship("campaign", campaign_id, "player", "user", viewer_id)

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
            headers=bearer(author_id),
        )
        assert pub_res.status_code == 201, pub_res.text
        entry_data = pub_res.json()
        entry_id = entry_data["entry_id"]
        assert entry_data["title"] == "Secret Journal of the Void"
        assert entry_data["status"] == "published"

        # 2. Author can read and update the private entry
        get_res = client.get(
            f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
            headers=bearer(author_id),
        )
        assert get_res.status_code == 200
        assert get_res.json()["title"] == "Secret Journal of the Void"

        # 3. Non-author viewer cannot read private entry
        viewer_get = client.get(
            f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
            headers=bearer(viewer_id),
        )
        assert viewer_get.status_code == 403

        # 4. Non-author viewer cannot edit private entry
        viewer_patch = client.patch(
            f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
            json={"title": "Hacked Title"},
            headers=bearer(viewer_id),
        )
        assert viewer_patch.status_code == 403

        # 5. Stranger (no campaign permissions) is forbidden from listing or editing
        stranger_list = client.get(
            f"/api/v1/campaigns/{campaign_id}/codex/entries",
            headers=bearer(stranger_id),
        )
        assert stranger_list.status_code == 403

        stranger_patch = client.patch(
            f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
            json={"title": "Stranger Hacked"},
            headers=bearer(stranger_id),
        )
        assert stranger_patch.status_code == 403

        # 6. Author updates entry privacy to party_shared
        author_patch = client.patch(
            f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
            json={"privacy": "party_shared", "title": "Revealed Sunken Tower"},
            headers=bearer(author_id),
        )
        assert author_patch.status_code == 200
        assert author_patch.json()["privacy"] == "party_shared"

        # 7. Now viewer (who has campaign play permission) can read the entry
        viewer_shared_get = client.get(
            f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
            headers=bearer(viewer_id),
        )
        assert viewer_shared_get.status_code == 200
        assert viewer_shared_get.json()["title"] == "Revealed Sunken Tower"


@pytest.mark.asyncio
async def test_frontdoor_permissions_evaluation() -> None:
    """Verify all extracted permission checks evaluate correctly with Zanzibar schema."""
    spicedb = get_spicedb_client()
    campaign_id = uuid4()
    cid_str = str(campaign_id)
    dm_user = f"dm-{uuid4()}"
    player_user = f"player-{uuid4()}"
    guest_user = f"guest-{uuid4()}"

    # Setup roles: DM is a dungeon_master, player is a player, guest is a spectator
    await spicedb.write_relationship("campaign", cid_str, "dungeon_master", "user", dm_user)
    await spicedb.write_relationship("campaign", cid_str, "player", "user", player_user)
    await spicedb.write_relationship("campaign", cid_str, "spectator", "user", guest_user)

    # Secrets: only DM can read secrets
    assert await permissions.check_user_can_read_secrets(dm_user, campaign_id, spicedb) is True
    assert await permissions.check_user_can_read_secrets(player_user, campaign_id, spicedb) is False
    assert await permissions.check_user_can_read_secrets(guest_user, campaign_id, spicedb) is False

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
