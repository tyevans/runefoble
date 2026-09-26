"""Comprehensive verification of eventsource-py integration across Runefoble."""

from uuid import uuid4

import pytest
from board_state.aggregate import BoardAggregate
from character_sheet.aggregate import CharacterAggregate
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain.event_registry import is_event_registered
from game_session.aggregate import GameSessionAggregate
from runefoble_events.events import (
    AbsencePenaltyApplied,
    BoardGridInitialized,
    CharacterCreated,
    SessionCreated,
    TokenMoved,
    TokenPlaced,
    TurnAdvanced,
)


def test_domain_events_registered_in_eventsource_registry():
    """Verify that all core Runefoble events are registered in eventsource-py EventRegistry."""
    core_events = [
        SessionCreated,
        TurnAdvanced,
        BoardGridInitialized,
        TokenPlaced,
        TokenMoved,
        CharacterCreated,
        AbsencePenaltyApplied,
    ]
    for evt_cls in core_events:
        assert is_event_registered(evt_cls.__name__), (
            f"Event '{evt_cls.__name__}' not registered in eventsource-py registry"
        )


@pytest.mark.asyncio
async def test_game_session_aggregate_lifecycle():
    """Test full event-sourced lifecycle of GameSessionAggregate."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=GameSessionAggregate)

    session_id = uuid4()
    campaign_id = uuid4()
    char_id = uuid4()

    # 1. Create session
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=campaign_id, title="The Sunless Citadel", dm_id="the_watcher")
    assert session.state.status == "lobby"
    assert session.state.current_turn == 1

    # 2. Player joins
    session.join_player(
        player_id="player-1",
        character_id=char_id,
        character_name="Valeros",
        character_class="Fighter",
    )
    assert "player-1" in session.state.participants

    # 3. Start session
    session.start()
    assert session.state.status == "active"

    # 4. Advance turns
    session.advance_turn(active_character_id=char_id)
    session.advance_turn(active_character_id=char_id)
    assert session.state.current_turn == 3

    # 5. Player leaves / absent -> stand-in activated
    session.leave_player("player-1", reason="Family emergency")
    assert session.state.participants["player-1"].is_stand_in_active is True
    assert session.state.participants["player-1"].is_present is False

    # Persist uncommitted events
    await repo.save(session)

    # 6. Reconstitute aggregate from event store
    reconstituted = await repo.load(session_id)
    assert reconstituted.version == session.version
    assert reconstituted.state.status == "active"
    assert reconstituted.state.current_turn == 3
    assert reconstituted.state.participants["player-1"].is_stand_in_active is True


@pytest.mark.asyncio
async def test_board_aggregate_spatial_mechanics():
    """Test BoardAggregate grid bounds, token movements, and event replay."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=BoardAggregate)

    board_id = uuid4()
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=10, rows=10, session_id="test-session")

    # Place tokens
    board.place_token("hero-1", name="Merisiel", token_type="pc", x=2, y=2, is_friendly=True)
    board.place_token("mob-1", name="Goblin Guard", token_type="monster", x=6, y=6)
    assert len(board.state.tokens) == 2

    # Move token
    board.move_token("hero-1", to_x=3, to_y=4)
    assert board.state.tokens["hero-1"].x == 3
    assert board.state.tokens["hero-1"].y == 4

    # Out-of-bounds move must raise ValueError
    with pytest.raises(ValueError, match="out of bounds"):
        board.move_token("hero-1", to_x=15, to_y=15)

    # Save and reload from event stream
    await repo.save(board)
    loaded = await repo.load(board_id)
    assert loaded.state.tokens["hero-1"].x == 3
    assert loaded.state.tokens["hero-1"].y == 4
    assert "mob-1" in loaded.state.tokens


@pytest.mark.asyncio
async def test_character_aggregate_with_penalties():
    """Test CharacterAggregate health tracking and session absence penalties."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=CharacterAggregate)

    char_id = uuid4()
    char = CharacterAggregate(char_id)
    char.create(name="Kyra", character_class="Cleric", max_hp=30)
    assert char.state.current_hp == 30

    # Apply damage and healing
    char.modify_health(-12, source="goblin arrow")
    assert char.state.current_hp == 18
    char.modify_health(5, source="cure wounds")
    assert char.state.current_hp == 23

    # Apply DM absence penalties ("drunk" and "foolishness")
    char.apply_penalty(
        penalty_type="drunk",
        description="Imbibed too heavily at the local tavern. Disadvantage on perception.",
        imposed_by="human_dm",
    )
    char.apply_penalty(
        penalty_type="foolishness",
        description="AI stand-in will make boastful and reckless tactical decisions.",
        imposed_by="the_watcher",
    )
    assert "drunk" in char.state.penalties
    assert "foolishness" in char.state.penalties

    # Persist and reconstitute
    await repo.save(char)
    reconstituted = await repo.load(char_id)
    assert reconstituted.state.current_hp == 23
    assert "drunk" in reconstituted.state.penalties

    # Clear penalty
    reconstituted.clear_penalty("drunk")
    assert "drunk" not in reconstituted.state.penalties
    await repo.save(reconstituted)

    final = await repo.load(char_id)
    assert "drunk" not in final.state.penalties
    assert "foolishness" in final.state.penalties
