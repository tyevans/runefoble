"""Blackbox frontdoor tests for The Watcher speech-to-intent and board actions."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import SpeechIntentParsed, TokenMoved, WatcherNarrationGenerated
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.mark.asyncio
async def test_blackbox_coordinate_movement_frontdoor(mock_redis: MockAsyncRedis):
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-1",
                "speaker_name": "Valeros",
                "transcript": "move to 6, 8",
                "session_id": str(uuid.uuid4()),
                "campaign_id": str(uuid.uuid4()),
                "token_id": "tok-valeros",
                "from_x": 2,
                "from_y": 2,
                "grid_cols": 12,
                "grid_rows": 12,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "move"
        assert data["parameters"]["to_x"] == 6
        assert data["parameters"]["to_y"] == 8

    # Verify observable domain events on Redis Streams frontdoor
    watcher_entries = mock_redis.streams.get("runefoble.events.watcher", [])
    assert len(watcher_entries) == 2
    evt1 = deserialize_event(watcher_entries[0][1])
    assert isinstance(evt1, SpeechIntentParsed)
    assert evt1.action_type == "move"

    evt2 = deserialize_event(watcher_entries[1][1])
    assert isinstance(evt2, WatcherNarrationGenerated)

    board_entries = mock_redis.streams.get("runefoble.events.board", [])
    assert len(board_entries) == 1
    board_evt = deserialize_event(board_entries[0][1])
    assert isinstance(board_evt, TokenMoved)
    assert board_evt.to_x == 6 and board_evt.to_y == 8


@pytest.mark.asyncio
async def test_blackbox_cardinal_movement_with_boundary_clamping(mock_redis: MockAsyncRedis):
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-2",
                "speaker_name": "Merisiel",
                "transcript": "advance 20 squares east",
                "session_id": str(uuid.uuid4()),
                "campaign_id": str(uuid.uuid4()),
                "token_id": "tok-meri",
                "from_x": 5,
                "from_y": 5,
                "grid_cols": 10,
                "grid_rows": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "move"
        assert data["parameters"]["direction"] == "east"

    # Clamped to grid_cols - 1 = 9
    board_entries = mock_redis.streams.get("runefoble.events.board", [])
    assert len(board_entries) == 1
    board_evt = deserialize_event(board_entries[0][1])
    assert isinstance(board_evt, TokenMoved)
    assert board_evt.to_x == 9 and board_evt.to_y == 5


@pytest.mark.asyncio
async def test_blackbox_intent_endpoint_attack_and_spell(mock_redis: MockAsyncRedis):
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attack
        resp_attack = await client.post(
            "/api/v1/watcher/intent",
            json={
                "speaker_id": "spk-3",
                "speaker_name": "Valeros",
                "transcript": "attack skeleton with mace",
                "session_id": str(uuid.uuid4()),
                "campaign_id": str(uuid.uuid4()),
            },
        )
        assert resp_attack.status_code == 200
        att_data = resp_attack.json()
        assert att_data["action_type"] == "attack"
        assert att_data["parameters"]["target"] == "skeleton"
        assert att_data["parameters"]["weapon"] == "mace"

        # Spell
        resp_spell = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-4",
                "speaker_name": "Ezren",
                "transcript": "cast magic missile at goblin archer",
                "session_id": str(uuid.uuid4()),
                "campaign_id": str(uuid.uuid4()),
            },
        )
        assert resp_spell.status_code == 200
        spell_data = resp_spell.json()
        assert spell_data["action_type"] == "cast_spell"
        assert spell_data["parameters"]["spell"] == "magic missile"


@pytest.mark.asyncio
async def test_blackbox_skill_check_and_dice_roll_frontdoors(mock_redis: MockAsyncRedis):
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Skill check
        resp_skill = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-5",
                "speaker_name": "Kyra",
                "transcript": "make a religion check",
                "session_id": str(uuid.uuid4()),
                "campaign_id": str(uuid.uuid4()),
            },
        )
        assert resp_skill.status_code == 200
        assert resp_skill.json()["action_type"] == "skill_check"
        assert resp_skill.json()["parameters"]["skill"] == "religion"

        # Dice roll
        resp_roll = await client.post(
            "/api/v1/watcher/intent",
            json={
                "speaker_id": "spk-6",
                "speaker_name": "Ezren",
                "transcript": "roll 2d6+3",
                "session_id": str(uuid.uuid4()),
                "campaign_id": str(uuid.uuid4()),
            },
        )
        assert resp_roll.status_code == 200
        assert resp_roll.json()["action_type"] == "roll_dice"
        assert resp_roll.json()["parameters"]["notation"] == "2d6+3"
