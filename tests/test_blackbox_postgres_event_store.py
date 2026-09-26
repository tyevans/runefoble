"""Blackbox TDD frontdoor test suite for PostgreSQL event store persistence.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind (postgres.yaml)
- ADR-0008: Property and Mutation Testing Strategy
- ADR-0011: Core Event Sourcing with eventsource-py (PostgreSQLEventStore)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Verifies:
1. Auto-creation of events schema upon first access.
2. End-to-end aggregate roundtrips (GameSessionAggregate, CharacterAggregate, BoardAggregate)
   persisted durably to PostgreSQL and replayed accurately.
3. Optimistic concurrency control across concurrent writers.
4. Raw stream inspection and event envelope durability checks.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from board_state.aggregate import BoardAggregate
from character_sheet.aggregate import CharacterAggregate
from eventsource import OptimisticLockError, StreamId
from game_session.aggregate import GameSessionAggregate
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    PostgreSQLEventStore,
    create_aggregate_repository,
    get_event_store,
    set_event_store,
)


@pytest.fixture(autouse=True)
def reset_event_store_singleton():
    """Reset global event store singleton between tests."""
    set_event_store(None)
    yield
    set_event_store(None)


@pytest.mark.asyncio
async def test_postgres_event_store_durable_aggregate_roundtrip(postgres_service):
    """Verify end-to-end durable event sourcing and reconstitution against PostgreSQL."""
    if not postgres_service:
        pytest.skip("Docker not available for PostgreSQL event store test")

    settings = PlatformSettings(
        database_url=str(postgres_service["dsn"]),
        use_postgres_event_store=True,
    )

    store = get_event_store(settings=settings, force_new=True)
    assert isinstance(store, PostgreSQLEventStore)

    # 1. GameSessionAggregate Lifecycle
    session_repo = create_aggregate_repository(GameSessionAggregate, event_store=store)
    session_id = uuid4()
    campaign_id = uuid4()
    char_id = uuid4()

    session = GameSessionAggregate(session_id)
    session.create(campaign_id=campaign_id, title="Vault of the Duergar", dm_id="the_watcher")
    session.join_player("player-valeros", char_id, "Valeros", "Fighter")
    session.start()
    session.advance_turn(active_character_id=char_id)
    session.advance_turn(active_character_id=char_id)
    session.leave_player("player-valeros", reason="Connection dropped")

    await session_repo.save(session)

    # 2. CharacterAggregate Lifecycle
    char_repo = create_aggregate_repository(CharacterAggregate, event_store=store)
    char = CharacterAggregate(char_id)
    char.create(name="Valeros", character_class="Fighter", max_hp=40)
    char.modify_health(-15, source="Crossbow trap")
    char.apply_penalty("drunk", "Celebrated before the dungeon", imposed_by="human_dm")
    char.apply_penalty("foolishness", "Charges heedlessly", imposed_by="the_watcher")

    await char_repo.save(char)

    # 3. BoardAggregate Lifecycle
    board_repo = create_aggregate_repository(BoardAggregate, event_store=store)
    board_id = uuid4()
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=12, rows=12, session_id=str(session_id))
    board.place_token("tok-valeros", name="Valeros", token_type="pc", x=3, y=3, is_friendly=True)
    board.place_token("tok-goblin", name="Goblin Archer", token_type="monster", x=7, y=8)
    board.move_token("tok-valeros", to_x=4, to_y=4)

    await board_repo.save(board)

    # 4. Verify durable reconstitution from a fresh repository instance
    fresh_session_repo = create_aggregate_repository(GameSessionAggregate, event_store=store)
    reloaded_session = await fresh_session_repo.load(session_id)
    assert reloaded_session.version == session.version
    assert reloaded_session.state.status == "active"
    assert reloaded_session.state.current_turn == 3
    assert "player-valeros" in reloaded_session.state.participants
    assert reloaded_session.state.participants["player-valeros"].is_stand_in_active is True

    fresh_char_repo = create_aggregate_repository(CharacterAggregate, event_store=store)
    reloaded_char = await fresh_char_repo.load(char_id)
    assert reloaded_char.version == char.version
    assert reloaded_char.state.current_hp == 25
    assert "drunk" in reloaded_char.state.penalties
    assert "foolishness" in reloaded_char.state.penalties

    fresh_board_repo = create_aggregate_repository(BoardAggregate, event_store=store)
    reloaded_board = await fresh_board_repo.load(board_id)
    assert reloaded_board.version == board.version
    assert reloaded_board.state.tokens["tok-valeros"].x == 4
    assert reloaded_board.state.tokens["tok-valeros"].y == 4
    assert "tok-goblin" in reloaded_board.state.tokens

    # 5. Clean up store engine
    await store.close()


@pytest.mark.asyncio
async def test_postgres_event_store_optimistic_concurrency(postgres_service):
    """Verify optimistic concurrency conflict detection in PostgreSQL event store."""
    if not postgres_service:
        pytest.skip("Docker not available for concurrency test")

    settings = PlatformSettings(
        database_url=str(postgres_service["dsn"]),
        use_postgres_event_store=True,
    )
    store = get_event_store(settings=settings, force_new=True)
    repo = create_aggregate_repository(CharacterAggregate, event_store=store)

    char_id = uuid4()
    char = CharacterAggregate(char_id)
    char.create(name="Seoni", character_class="Sorcerer", max_hp=28)
    await repo.save(char)

    # Concurrent readers load same aggregate state
    replica_a = await repo.load(char_id)
    replica_b = await repo.load(char_id)

    # Writer A mutates and saves first
    replica_a.modify_health(-5, source="Magic Missile")
    await repo.save(replica_a)

    # Writer B attempts to commit on stale version
    replica_b.modify_health(-10, source="Fireball")
    with pytest.raises(OptimisticLockError):
        await repo.save(replica_b)

    await store.close()


@pytest.mark.asyncio
async def test_postgres_raw_event_stream_verification(postgres_service):
    """Verify raw stream event envelop reading directly through PostgreSQL store."""
    if not postgres_service:
        pytest.skip("Docker not available for stream verification test")

    settings = PlatformSettings(
        database_url=str(postgres_service["dsn"]),
        use_postgres_event_store=True,
    )
    store = get_event_store(settings=settings, force_new=True)
    repo = create_aggregate_repository(GameSessionAggregate, event_store=store)

    session_id = uuid4()
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=uuid4(), title="Stream Inspection", dm_id="the_watcher")
    session.start()
    await repo.save(session)

    stream_id = StreamId(aggregate_id=session_id, category="GameSession")
    assert await store.get_stream_version(stream_id) == 2

    envelopes = [env async for env in store.read_stream(stream_id)]
    assert len(envelopes) == 2
    assert envelopes[0].event.__class__.__name__ == "SessionCreated"
    assert envelopes[1].event.__class__.__name__ == "SessionStarted"

    assert await store.event_exists(envelopes[0].event.event_id)

    await store.close()
