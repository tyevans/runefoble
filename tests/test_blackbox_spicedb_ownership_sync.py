"""Blackbox TDD frontdoor suite for SpiceDB resource ownership and edge cases.

Verifies:
1. Tactical board token movement authorization and player isolation.
2. Spectator read-only token inspection and mutation rejection.
3. GM universal token manipulation override.
4. Domain event stream synchronization (SessionCreated, ParticipantJoined, CharacterCreated).
5. Character ownership revocation and permission invalidation.
6. Error handling for malformed event payloads and invalid sync requests.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app
from runefoble_auth.listener import SpiceDBEventListener
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events import CharacterCreated, ParticipantJoined, SessionCreated
from runefoble_platform.bus import EventBus

client = TestClient(app)


@pytest.mark.asyncio
async def test_token_movement_player_isolation_and_spectator_readonly() -> None:
    """Players move own tokens, cannot move other player tokens; spectators are read-only."""
    campaign_id = f"camp-tactical-{uuid4().hex[:8]}"
    player_alice, player_bob = "alice_fighter", "bob_wizard"
    spectator_clara, gm_derek = "clara_audience", "derek_gm"

    char_alice, char_bob = f"char-a-{uuid4().hex[:8]}", f"char-b-{uuid4().hex[:8]}"
    token_alice, token_bob = f"tok-a-{uuid4().hex[:8]}", f"tok-b-{uuid4().hex[:8]}"

    # 1. Frontdoor sync: Memberships
    memberships = [
        (gm_derek, "gm"),
        (player_alice, "player"),
        (player_bob, "player"),
        (spectator_clara, "spectator"),
    ]
    for uid, role in memberships:
        client.post(
            "/api/v1/auth/sync/membership",
            json={"campaign_id": campaign_id, "user_id": uid, "role": role},
        )

    # 2. Frontdoor sync: Character ownerships and token bindings
    for cid, uid, tid in [
        (char_alice, player_alice, token_alice),
        (char_bob, player_bob, token_bob),
    ]:
        client.post(
            "/api/v1/auth/sync/character-ownership",
            json={"character_id": cid, "user_id": uid, "campaign_id": campaign_id},
        )
        client.post(
            "/api/v1/auth/sync/token-binding",
            json={"token_id": tid, "character_id": cid, "campaign_id": campaign_id},
        )

    # 4. Alice moves her own token -> Allowed (200)
    res_a = client.post(
        f"/api/v1/board/tokens/{token_alice}/move",
        headers={"X-User-Id": player_alice},
        json={"to_x": 4, "to_y": 5},
    )
    assert res_a.status_code == 200 and res_a.json()["status"] == "token_moved"

    # 5. Alice attempts to move Bob's token -> Denied (403)
    res_ab = client.post(
        f"/api/v1/board/tokens/{token_bob}/move",
        headers={"X-User-Id": player_alice},
        json={"to_x": 1, "to_y": 1},
    )
    assert res_ab.status_code == 403 and res_ab.json()["detail"]["required_permission"] == "move"

    # 6. Bob moves his own token -> Allowed (200)
    res_b = client.post(
        f"/api/v1/board/tokens/{token_bob}/move",
        headers={"X-User-Id": player_bob},
        json={"to_x": 6, "to_y": 7},
    )
    assert res_b.status_code == 200

    # 7. Bob attempts to move Alice's token -> Denied (403)
    res_ba = client.post(
        f"/api/v1/board/tokens/{token_alice}/move",
        headers={"X-User-Id": player_bob},
        json={"to_x": 0, "to_y": 0},
    )
    assert res_ba.status_code == 403

    # 8. Spectator Clara attempts to move Token Alice -> Denied (403)
    res_sp_move = client.post(
        f"/api/v1/board/tokens/{token_alice}/move",
        headers={"X-User-Id": spectator_clara},
        json={"to_x": 2, "to_y": 2},
    )
    assert res_sp_move.status_code == 403

    # 9. Spectator Clara inspects Token Alice -> Read-only Allowed (200)
    res_sp_inspect = client.get(
        f"/api/v1/board/tokens/{token_alice}",
        headers={"X-User-Id": spectator_clara},
    )
    assert res_sp_inspect.status_code == 200 and res_sp_inspect.json()["token_id"] == token_alice

    # 10. GM Derek can move any token in the campaign -> Allowed (200)
    assert (
        client.post(
            f"/api/v1/board/tokens/{token_alice}/move",
            headers={"X-User-Id": gm_derek},
            json={"to_x": 8, "to_y": 9},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/board/tokens/{token_bob}/move",
            headers={"X-User-Id": gm_derek},
            json={"to_x": 9, "to_y": 9},
        ).status_code
        == 200
    )


@pytest.mark.asyncio
async def test_domain_event_listeners_stream_synchronization() -> None:
    """Publishing domain events automatically provisions SpiceDB Zanzibar relationships."""
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    listener = SpiceDBEventListener(sync_service=sync_service)

    local_bus = EventBus()
    listener.register_bus_handlers(local_bus)

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
    await local_bus.publish("SessionCreated", session_event)
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", dm_id)

    # Publish ParticipantJoined -> player play & view permissions
    participant_event = ParticipantJoined(
        aggregate_id=uuid4(),
        campaign_id=campaign_id,
        user_id=player_id,
        role="player",
        character_id=char_id,
    )
    await local_bus.publish("ParticipantJoined", participant_event)
    assert await spicedb.check_permission("campaign", campaign_id, "play", "user", player_id)
    assert await spicedb.check_permission("campaign", campaign_id, "view", "user", player_id)

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
    await local_bus.publish("CharacterCreated", char_event)
    assert await spicedb.check_permission("character", str(char_id), "edit", "user", player_id)


@pytest.mark.asyncio
async def test_character_ownership_revocation_and_edge_cases() -> None:
    """Character ownership can be revoked, and malformed requests/events are safely handled."""
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    listener = SpiceDBEventListener(sync_service=sync_service)

    char_id = f"char-rev-{uuid4().hex[:8]}"
    user_id = f"user-rev-{uuid4().hex[:6]}"

    # Frontdoor bind character ownership
    res = client.post(
        "/api/v1/auth/sync/character-ownership",
        json={"character_id": char_id, "user_id": user_id},
    )
    assert res.status_code == 200
    assert await spicedb.check_permission("character", char_id, "edit", "user", user_id)

    # Revoke character owner relationship
    await spicedb.delete_relationship("character", char_id, "owner", "user", user_id)
    assert not await spicedb.check_permission("character", char_id, "edit", "user", user_id)

    # Frontdoor edge case: Malformed request payload -> 422 Unprocessable Entity
    res_invalid = client.post("/api/v1/auth/sync/character-ownership", json={"malformed": True})
    assert res_invalid.status_code == 422

    # Listener edge case: Malformed domain events return empty list without crashing
    assert await listener.on_character_created(object()) == []
    assert await listener.on_session_created(None) == []
    assert await listener.on_participant_joined(object()) == []
