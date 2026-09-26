"""Blackbox TDD tests for Mid-Session Hot-Swap Handoff and Session Takeover (TASK-0096, TASK-0055)."""

from uuid import uuid4

import pytest
from game_session.main import app as session_app
from game_session.main import set_event_bus as session_set_event_bus
from game_session.main import set_spicedb_client as session_set_spicedb
from httpx import ASGITransport, AsyncClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.events import CharacterControlTransferred
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
    deserialize_event,
)


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


# --- 1. Mid-Session Hot-Swap Takeover & Combat Order Continuity ---


@pytest.mark.asyncio
async def test_mid_session_hot_swap_takeover_and_turn_continuity(mock_redis: MockAsyncRedis):
    """POST /api/v1/sessions/{id}/hot-swap smoothly transfers control in <100ms, preserving combat order."""
    session_bus = RedisStreamsEventBus(client=mock_redis)
    session_set_event_bus(session_bus)
    spicedb = SpiceDBClient()
    session_set_spicedb(spicedb)

    async with AsyncClient(
        transport=ASGITransport(app=session_app), base_url="http://test"
    ) as client:
        campaign_id, char_id, player_id = str(uuid4()), str(uuid4()), "sarah-user"

        # 1. Setup session, join player, start session & combat encounter
        create_res = await client.post(
            "/api/v1/sessions/create",
            json={"campaign_id": campaign_id, "title": "Tomb of Horror", "dm_id": "the_watcher"},
        )
        session_id = create_res.json()["session_id"]
        await client.post(
            f"/api/v1/sessions/{session_id}/join",
            json={
                "player_id": player_id,
                "character_id": char_id,
                "character_name": "Kyra",
                "character_class": "Cleric",
            },
        )
        await client.post(f"/api/v1/sessions/{session_id}/start")
        await client.post(
            f"/api/v1/sessions/{session_id}/combat/start",
            json={
                "combatants": [
                    {"combatant_id": char_id, "combatant_name": "Kyra", "initiative_score": 18},
                    {
                        "combatant_id": "goblin-1",
                        "combatant_name": "Goblin Boss",
                        "initiative_score": 12,
                    },
                ]
            },
        )

        # 2. Player marks absent mid-encounter -> AI stand-in activates
        leave_res = await client.post(
            f"/api/v1/sessions/{session_id}/leave",
            json={"player_id": player_id, "reason": "Late arrival"},
        )
        assert leave_res.status_code == 200
        assert leave_res.json()["participants"][player_id]["is_stand_in_active"] is True

        # 3. Configure SpiceDB Zanzibar permission: Sarah owns character
        await spicedb.write_relationship(
            resource_type="character",
            resource_id=char_id,
            relation="owner",
            subject_type="user",
            subject_id=player_id,
        )

        # 4. Sarah reconnects and executes hot-swap takeover
        hot_swap_res = await client.post(
            f"/api/v1/sessions/{session_id}/hot-swap",
            json={"player_id": player_id, "character_id": char_id},
            headers={"x-user-id": player_id},
        )
        assert hot_swap_res.status_code == 200
        data = hot_swap_res.json()

        # Turn order continuity assertions
        assert data["previous_controller"] == "ai_stand_in" and data["new_controller"] == "player"
        assert data["in_combat"] is True and data["combat_round"] == 1
        assert data["combat_active_id"] == char_id
        session_state = data["session_state"]
        participant = session_state["participants"][player_id]
        assert participant["is_present"] is True and participant["is_stand_in_active"] is False

    # 5. Verify CharacterControlTransferred CloudEvent published to Redis Streams
    assert "runefoble.events.session" in mock_redis.streams
    events = [deserialize_event(f) for _, f in mock_redis.streams["runefoble.events.session"]]
    transfer = [e for e in events if isinstance(e, CharacterControlTransferred)]
    assert len(transfer) >= 1
    assert transfer[0].session_id == str(session_id) and transfer[0].character_id == str(char_id)
    assert transfer[0].player_id == player_id and transfer[0].new_controller == "player"


# --- 2. Hot-Swap Zanzibar Authorization Enforcement ---


@pytest.mark.asyncio
async def test_hot_swap_unauthorized_user_rejected_by_spicedb(mock_redis: MockAsyncRedis):
    """Unauthorized user without character/session permissions cannot hot-swap control."""
    session_bus = RedisStreamsEventBus(client=mock_redis)
    session_set_event_bus(session_bus)
    spicedb = SpiceDBClient()
    session_set_spicedb(spicedb)

    async with AsyncClient(
        transport=ASGITransport(app=session_app), base_url="http://test"
    ) as client:
        campaign_id, char_id, player_id = str(uuid4()), str(uuid4()), "sarah-user"
        create_res = await client.post(
            "/api/v1/sessions/create",
            json={"campaign_id": campaign_id, "title": "Crypt", "dm_id": "the_watcher"},
        )
        session_id = create_res.json()["session_id"]
        await client.post(
            f"/api/v1/sessions/{session_id}/join",
            json={"player_id": player_id, "character_id": char_id, "character_name": "Kyra"},
        )
        await client.post(f"/api/v1/sessions/{session_id}/start")

        # Rogue user attempts hot-swap without permissions
        unauth_res = await client.post(
            f"/api/v1/sessions/{session_id}/hot-swap",
            json={"player_id": "rogue-intruder", "character_id": char_id},
            headers={"x-user-id": "rogue-intruder"},
        )
        assert unauth_res.status_code == 403
        assert "does not have permission" in unauth_res.json()["detail"]
