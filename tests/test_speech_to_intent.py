"""Unit and integration tests for Speech-to-Intent Sub-500ms Pipeline (TASK-0002)."""

import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import (
    PlayerSpokeEvent,
    SpeechIntentParsed,
    TokenMoved,
    WatcherNarrationGenerated,
)
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
    deserialize_event,
)
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus
from the_watcher.watcher_ai import TheWatcherEngine
from voice_agent.main import app as voice_app
from voice_agent.main import set_event_bus as voice_set_event_bus


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def watcher_engine() -> TheWatcherEngine:
    return TheWatcherEngine()


# ---------------------------------------------------------------------------
# Unit Tests: Parsing Engine
# ---------------------------------------------------------------------------


def test_cardinal_movement_parsing(watcher_engine: TheWatcherEngine):
    # 1. Squares cardinal
    res1 = watcher_engine.parse_speech_intent("move 3 squares north", "Valeros")
    assert res1.action_type == "move"
    assert res1.parameters["steps"] == 3
    assert res1.parameters["direction"] == "north"
    assert res1.parameters["dx"] == 0
    assert res1.parameters["dy"] == -3
    assert "Valeros" in res1.watcher_reply

    # 2. Feet cardinal (5ft = 1 square)
    res2 = watcher_engine.parse_speech_intent("step 15 feet south", "Valeros")
    assert res2.action_type == "move"
    assert res2.parameters["steps"] == 3
    assert res2.parameters["direction"] == "south"
    assert res2.parameters["dx"] == 0
    assert res2.parameters["dy"] == 3

    # 3. Advance east
    res3 = watcher_engine.parse_speech_intent("advance 2 east", "Merisiel")
    assert res3.action_type == "move"
    assert res3.parameters["steps"] == 2
    assert res3.parameters["direction"] == "east"
    assert res3.parameters["dx"] == 2
    assert res3.parameters["dy"] == 0

    # 4. Retreat west
    res4 = watcher_engine.parse_speech_intent("retreat 1 west", "Kyra")
    assert res4.action_type == "move"
    assert res4.parameters["steps"] == 1
    assert res4.parameters["direction"] == "west"
    assert res4.parameters["dx"] == -1
    assert res4.parameters["dy"] == 0


def test_coordinate_movement_parsing(watcher_engine: TheWatcherEngine):
    res = watcher_engine.parse_speech_intent("move to 5, 8", "Ezren")
    assert res.action_type == "move"
    assert res.parameters["to_x"] == 5
    assert res.parameters["to_y"] == 8
    assert res.target == "5, 8"
    assert "5, 8" in res.watcher_reply


def test_target_token_and_flanking_movement(watcher_engine: TheWatcherEngine):
    # Move to target token
    res1 = watcher_engine.parse_speech_intent("move to the goblin archer", "Valeros")
    assert res1.action_type == "move"
    assert res1.parameters["target_token"] == "goblin archer"
    assert "goblin archer" in res1.watcher_reply

    # Flank token
    res2 = watcher_engine.parse_speech_intent("flank the skeleton", "Merisiel")
    assert res2.action_type == "move"
    assert res2.parameters["action"] == "flank"
    assert res2.parameters["target_token"] == "skeleton"
    assert "skeleton" in res2.watcher_reply


def test_attack_intent_parsing(watcher_engine: TheWatcherEngine):
    # Specific attack with weapon
    res1 = watcher_engine.parse_speech_intent("attack goblin with longsword", "Valeros")
    assert res1.action_type == "attack"
    assert res1.parameters["target"] == "goblin"
    assert res1.parameters["weapon"] == "longsword"
    assert "goblin" in res1.watcher_reply
    assert "longsword" in res1.watcher_reply

    # Slash with sword
    res2 = watcher_engine.parse_speech_intent("I slash at the goblin with my sword!", "Valeros")
    assert res2.action_type == "attack"
    assert res2.parameters["target"] == "goblin"


def test_spellcasting_intent_parsing(watcher_engine: TheWatcherEngine):
    # Spell at coordinates
    res1 = watcher_engine.parse_speech_intent("cast fireball at 4, 6", "Ezren")
    assert res1.action_type == "cast_spell"
    assert res1.parameters["spell"] == "fireball"
    assert res1.parameters["target_x"] == 4
    assert res1.parameters["target_y"] == 6
    assert "fireball" in res1.watcher_reply

    # Spell at target token
    res2 = watcher_engine.parse_speech_intent("cast magic missile at goblin archer", "Ezren")
    assert res2.action_type == "cast_spell"
    assert res2.parameters["spell"] == "magic missile"
    assert res2.target == "goblin archer"


def test_skill_check_intent_parsing(watcher_engine: TheWatcherEngine):
    res1 = watcher_engine.parse_speech_intent("stealth check", "Merisiel")
    assert res1.action_type == "skill_check"
    assert res1.parameters["skill"] == "stealth"
    assert res1.parameters["dice_notation"] == "1d20"

    res2 = watcher_engine.parse_speech_intent("make an athletics check", "Valeros")
    assert res2.action_type == "skill_check"
    assert res2.parameters["skill"] == "athletics"


def test_sub_200ms_latency_budget(watcher_engine: TheWatcherEngine):
    """Verify that heuristic parsing latency budget is strictly under 200ms."""
    phrases = [
        ("step 15 feet south", "Valeros"),
        ("move to 5, 8", "Ezren"),
        ("attack goblin with longsword", "Valeros"),
        ("cast fireball at 4, 6", "Ezren"),
        ("stealth check", "Merisiel"),
        ("flank the skeleton", "Merisiel"),
    ]
    latencies = []
    for _ in range(50):
        for phrase, speaker in phrases:
            t0 = time.perf_counter()
            watcher_engine.parse_speech_intent(phrase, speaker)
            latencies.append((time.perf_counter() - t0) * 1000)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    # Heuristic parsing must be well under 200ms (typically < 1ms)
    assert max_latency < 200.0, f"Max latency exceeded 200ms: {max_latency:.2f}ms"
    assert avg_latency < 10.0, f"Average latency too high: {avg_latency:.2f}ms"


# ---------------------------------------------------------------------------
# Integration Tests: Redis Streams Event Dispatching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watcher_redis_stream_event_emission(mock_redis: MockAsyncRedis):
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    session_id = str(uuid.uuid4())
    campaign_id = str(uuid.uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "valeros-1",
                "speaker_name": "Valeros",
                "transcript": "step 15 feet south",
                "session_id": session_id,
                "campaign_id": campaign_id,
                "token_id": "tok-valeros",
                "from_x": 3,
                "from_y": 2,
                "grid_cols": 12,
                "grid_rows": 12,
            },
        )
        assert resp.status_code == 200
        intent = resp.json()
        assert intent["action_type"] == "move"
        assert intent["parameters"]["steps"] == 3

    # Verify runefoble.events.watcher stream received SpeechIntentParsed & WatcherNarrationGenerated
    assert "runefoble.events.watcher" in mock_redis.streams
    watcher_entries = mock_redis.streams["runefoble.events.watcher"]
    assert len(watcher_entries) == 2

    # First event: SpeechIntentParsed
    _id1, fields1 = watcher_entries[0]
    parsed1 = deserialize_event(fields1)
    assert isinstance(parsed1, SpeechIntentParsed)
    assert parsed1.speaker_name == "Valeros"
    assert parsed1.action_type == "move"
    assert parsed1.raw_transcript == "step 15 feet south"

    # Second event: WatcherNarrationGenerated
    _id2, fields2 = watcher_entries[1]
    parsed2 = deserialize_event(fields2)
    assert isinstance(parsed2, WatcherNarrationGenerated)
    assert "Valeros" in parsed2.narrative_text

    # Verify runefoble.events.board stream received TokenMoved
    assert "runefoble.events.board" in mock_redis.streams
    board_entries = mock_redis.streams["runefoble.events.board"]
    assert len(board_entries) == 1

    _id_board, fields_board = board_entries[0]
    parsed_board = deserialize_event(fields_board)
    assert isinstance(parsed_board, TokenMoved)
    assert parsed_board.token_id == "tok-valeros"
    assert parsed_board.name == "Valeros"
    assert parsed_board.from_x == 3
    assert parsed_board.from_y == 2
    assert parsed_board.to_x == 3
    assert parsed_board.to_y == 5  # 2 + 3 squares south


@pytest.mark.asyncio
async def test_voice_agent_transcription_and_event_emission(mock_redis: MockAsyncRedis):
    event_bus = RedisStreamsEventBus(client=mock_redis)
    voice_set_event_bus(event_bus)

    session_id = str(uuid.uuid4())
    campaign_id = str(uuid.uuid4())

    transport = ASGITransport(app=voice_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voice/transcribe",
            json={
                "speaker_id": "kyra-1",
                "speaker_name": "Kyra",
                "session_id": session_id,
                "campaign_id": campaign_id,
                "transcript": "advance 2 east",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"] == "advance 2 east"
        assert data["speaker_name"] == "Kyra"

    # Verify PlayerSpokeEvent was emitted to runefoble.events.session
    assert "runefoble.events.session" in mock_redis.streams
    session_entries = mock_redis.streams["runefoble.events.session"]
    assert len(session_entries) == 1

    _id, fields = session_entries[0]
    event = deserialize_event(fields)
    assert isinstance(event, PlayerSpokeEvent)
    assert event.speaker_name == "Kyra"
    assert event.transcript == "advance 2 east"
