"""Tests for SessionReadProjection domain event handling and background worker processing."""

from uuid import uuid4

import pytest
from game_session.projections import SessionReadProjection
from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
    TurnAdvanced,
)
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def consumer_group(mock_redis: MockAsyncRedis) -> RedisConsumerGroup:
    return RedisConsumerGroup(client=mock_redis)


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=mock_redis)


@pytest.mark.asyncio
async def test_session_read_projection_applies_events() -> None:
    projection = SessionReadProjection()
    session_id = uuid4()
    str_sess_id = str(session_id)

    # 1. Session created
    projection.apply_event(SessionCreated(aggregate_id=session_id, title="Curse of Strahd"))
    view = projection.get_session(session_id)
    assert view is not None
    assert view.title == "Curse of Strahd"
    assert view.status == "lobby"
    assert view.event_count == 1

    # 2. Session started
    projection.apply_event(SessionStarted(aggregate_id=session_id))
    assert projection.get_session(session_id).status == "active"

    # 3. Token placed
    projection.apply_event(
        TokenPlaced(
            aggregate_id=session_id,
            token_id="tok-1",
            name="Paladin Sir Gareth",
            token_type="pc",
            x=10,
            y=12,
            hp=50,
            is_friendly=True,
        )
    )
    token = projection.get_token(session_id, "tok-1")
    assert token is not None
    assert token.name == "Paladin Sir Gareth"
    assert token.x == 10
    assert token.y == 12

    # 4. Token moved
    projection.apply_event(
        TokenMoved(
            aggregate_id=session_id,
            token_id="tok-1",
            name="Paladin Sir Gareth",
            from_x=10,
            from_y=12,
            to_x=15,
            to_y=18,
        )
    )
    updated_token = projection.get_token(session_id, "tok-1")
    assert updated_token.x == 15
    assert updated_token.y == 18

    # 5. Scene atmosphere set
    projection.apply_event(
        SceneAtmosphereSet(
            session_id=str_sess_id,
            scene_id="scene-404",
            location_name="Castle Crypt",
            lighting="torchlit",
            mood="dread",
            description="Shadows flicker across ancient stone coffins.",
            ambient_audio_prompt="echoing water drips and distant howling",
        )
    )
    atmosphere = projection.get_atmosphere(session_id)
    assert atmosphere is not None
    assert atmosphere.location_name == "Castle Crypt"
    assert atmosphere.mood == "dread"

    # 6. Encounter spawned
    projection.apply_event(
        EncounterSpawned(
            session_id=str_sess_id,
            encounter_id="enc-9",
            encounter_name="Gargoyle Ambush",
            threat_level="high",
            monsters=[{"name": "Stone Gargoyle", "count": 2}],
            tactical_objective="Defend the crypt entrance",
        )
    )
    encounters = projection.get_encounters(session_id)
    assert "enc-9" in encounters
    assert encounters["enc-9"].threat_level == "high"

    # 7. Action resolved in combat log
    projection.apply_event(
        AutonomousActionResolved(
            session_id=str_sess_id,
            actor_name="Stone Gargoyle",
            action_type="Claw Slash",
            target_name="Paladin Sir Gareth",
            narrative="Gargoyle swoops down and slashes armor",
            hp_impact=-8,
        )
    )
    log = projection.get_combat_log(session_id)
    assert len(log) == 1
    assert log[0]["action_type"] == "Claw Slash"
    assert log[0]["hp_impact"] == -8

    # 8. Turn advanced
    projection.apply_event(TurnAdvanced(aggregate_id=session_id, previous_turn=1, new_turn=2))
    assert projection.get_session(session_id).current_turn == 2

    # 9. Token removed
    projection.apply_event(TokenRemoved(aggregate_id=session_id, token_id="tok-1"))
    assert projection.get_token(session_id, "tok-1") is None

    # 10. Session ended
    projection.apply_event(SessionEnded(aggregate_id=session_id))
    assert projection.get_session(session_id).status == "ended"
    assert projection.get_session(session_id).event_count == 10


@pytest.mark.asyncio
async def test_session_read_projection_worker_process_loop(
    consumer_group: RedisConsumerGroup,
    event_bus: RedisStreamsEventBus,
    mock_redis: MockAsyncRedis,
) -> None:
    stream = "runefoble.events.session"
    group = "session_projection_group"
    projection = SessionReadProjection(
        consumer_group=consumer_group,
        stream=stream,
        group_name=group,
        consumer_name="proj_worker_alpha",
    )

    session_id = uuid4()
    str_sess_id = str(session_id)

    # Publish initial session event
    await event_bus.publish_event(
        stream,
        SessionCreated(aggregate_id=session_id, title="Lost Mine of Phandelver"),
    )
    await event_bus.publish_event(
        stream,
        TokenPlaced(
            aggregate_id=session_id,
            token_id="tok-goblin",
            name="Goblin Archer",
            x=3,
            y=4,
            token_type="monster",
            hp=7,
        ),
    )

    # Start projection worker
    await projection.start()
    assert projection.running is True

    # Process events
    processed = await projection.process_once()
    assert processed == 2

    # Verify projection read state
    view = projection.get_session(str_sess_id)
    assert view is not None
    assert view.title == "Lost Mine of Phandelver"
    assert "tok-goblin" in view.tokens
    assert view.tokens["tok-goblin"].x == 3

    # All processed messages should be ACKed
    assert len(mock_redis.get_pending(stream, group)) == 0

    # Test poison event handling: bad dict causing exception inside apply_event
    class ExplodingEvent:
        pass

    # A malformed event that raises during apply
    await mock_redis.xadd(
        stream,
        {"event_type": "CorruptEvent", "payload": "non-json-invalid{"},
    )

    # Monkey-patch apply_event on a specific condition or corrupt entry
    def broken_apply(event: object) -> None:
        raise RuntimeError("Unrecoverable deserialization fault")

    original_apply = projection.apply_event
    projection.apply_event = broken_apply

    processed_corrupt = await projection.process_once()
    assert processed_corrupt == 0  # Failed, routed to DLQ

    # Verify DLQ received the poison pill
    dlq_stream = f"{stream}.dlq"
    assert dlq_stream in mock_redis.streams
    assert len(mock_redis.streams[dlq_stream]) == 1
    assert (
        "Unrecoverable deserialization fault"
        in mock_redis.streams[dlq_stream][0][1]["error_reason"]
    )

    # Pending list is still 0 because poison message was ACKed after DLQ routing
    assert len(mock_redis.get_pending(stream, group)) == 0

    projection.apply_event = original_apply

    # Graceful stop
    await projection.stop()
    assert projection.running is False
