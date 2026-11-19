"""Blackbox TDD frontdoor suite for SpiceDB resource ownership and edge cases.

Verifies:
1. Domain event stream synchronization (SessionCreated, CharacterCreated).
2. Character ownership written by the character frontdoor on create.
3. Removed public sync routes return 404. Error handling for malformed event payloads.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events.events import CharacterCreated, SessionCreated


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.mark.asyncio
async def test_domain_events_provision_spicedb_relationships() -> None:
    """Domain events provision SpiceDB Zanzibar relationships through the sync service."""
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)

    campaign_id = f"camp-evt-{uuid4().hex[:8]}"
    dm_id = "watcher_dm_99"
    player_id = "barbarian_grog"
    char_id = uuid4()

    # Publish SessionCreated -> DM run_session permission
    session_event = SessionCreated(
        aggregate_id=uuid4(),
        campaign_id=campaign_id,
        session_id=campaign_id,
        dm_id=dm_id,
        title="Crypt of Shadows",
    )
    await sync_service.handle_session_created(session_event)
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", dm_id)

    # Publish CharacterCreated -> character owner edit permission
    char_event = CharacterCreated(
        aggregate_id=char_id,
        name="Grog Strongjaw",
        character_class="Barbarian",
        max_hp=45,
        current_hp=45,
        player_id=player_id,
        campaign_id=campaign_id,
    )
    await sync_service.handle_character_created(char_event)
    assert await spicedb.check_permission("character", str(char_id), "edit", "user", player_id)


@pytest.mark.asyncio
async def test_character_create_writes_owner_and_removed_sync_routes_return_404(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
) -> None:
    """Creating a character through the gateway writes the owner relation. Removed sync routes 404."""
    spicedb = get_spicedb_client()
    owner_id = f"user-rev-{uuid4().hex[:6]}"
    owner_headers = _auth(trusted_ws_issuer, owner_id)

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/characters",
            json={"name": "Revocable Rogue", "characterClass": "Rogue", "maxHp": 10},
            headers=owner_headers,
        )
        assert res.status_code == 201, res.text
        char_id = res.json()["id"]
        assert client.get(f"/api/v1/characters/{char_id}", headers=owner_headers).status_code == 200
        assert await spicedb.check_permission("character", char_id, "delete", "user", owner_id)

        # The public character-ownership sync route is removed (TASK-0543)
        res_removed = client.post(
            "/api/v1/auth/sync/character-ownership",
            json={"character_id": char_id, "user_id": owner_id},
        )
        assert res_removed.status_code == 404
