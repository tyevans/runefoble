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
    CombatEncounterEnded,
    CombatEncounterStarted,
    InitiativeRolled,
    InitiativeTurnAdvanced,
    SessionCreated,
    TokenMoved,
    TokenPlaced,
    TurnAdvanced,
)
from runefoble_platform.identifiers import opaque_aggregate_id
from soundscape.aggregate import SoundscapeAggregate


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
        CombatEncounterStarted,
        InitiativeRolled,
        InitiativeTurnAdvanced,
        CombatEncounterEnded,
    ]
    for evt_cls in core_events:
        assert is_event_registered(evt_cls.event_type_name()), (
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


@pytest.mark.asyncio
async def test_unit_board_aggregate_modular_handlers_round_trip():
    """Verify event-sourced BoardAggregate reconstitution using modular handler mixins."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=BoardAggregate)

    board_id = uuid4()
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=10, rows=10, session_id="test-session-modular")

    # 1. Configure difficult terrain and lava hazard
    board.configure_terrain(x=3, y=3, elevation=1, terrain_type="difficult", hazard="lava")
    assert board.get_terrain(3, 3).terrain_type == "difficult"
    assert board.get_terrain(3, 3).hazard == "lava"

    # 2. Place friendly player token
    board.place_token(
        token_id="valeros",
        name="Valeros",
        token_type="pc",
        x=1,
        y=1,
        hp=35,
        is_friendly=True,
        vision_radius=2,
    )
    assert "valeros" in board.state.tokens
    assert board.state.tokens["valeros"].x == 1
    assert board.state.tokens["valeros"].y == 1

    # 3. Move token across hazard at (3, 3) to (4, 4)
    outcome = board.move_token("valeros", to_x=4, to_y=4)
    assert board.state.tokens["valeros"].x == 4
    assert board.state.tokens["valeros"].y == 4
    assert outcome.hazard_triggered == "lava"
    assert outcome.damage_dice == "2d10"
    assert outcome.movement_cost > 0

    # 4. Execute tactical token action
    board.execute_token_action(
        token_id="valeros",
        action="dodge",
        details={"stance": "defensive"},
        initiated_by="player",
    )
    assert board.state.tokens["valeros"].active_action == "dodge"

    # 5. Place AoE spell template
    board.place_aoe_template(
        template_id="fireball-1",
        shape="circle",
        origin_x=4.0,
        origin_y=4.0,
        radius_ft=20.0,
        spell_name="Fireball",
        affected_token_ids=["valeros"],
    )
    assert len(board.state.active_aoe_templates) == 1
    assert board.state.active_aoe_templates[0].template_id == "fireball-1"

    # 6. Save aggregate to event store
    await repo.save(board)

    # 7. Reconstitute from event stream and verify all modular handler states match
    reconstituted = await repo.load(board_id)
    assert reconstituted.state.cols == 10
    assert reconstituted.state.rows == 10
    assert reconstituted.state.tokens["valeros"].x == 4
    assert reconstituted.state.tokens["valeros"].y == 4
    assert reconstituted.state.tokens["valeros"].active_action == "dodge"
    assert len(reconstituted.state.active_aoe_templates) == 1
    assert reconstituted.get_terrain(3, 3).hazard == "lava"

    # 8. Remove AoE template and token on reconstituted aggregate
    reconstituted.remove_aoe_template("fireball-1")
    assert len(reconstituted.state.active_aoe_templates) == 0

    reconstituted.remove_token("valeros", reason="extracted")
    assert "valeros" not in reconstituted.state.tokens


@pytest.mark.asyncio
async def test_unit_cast_spell_domain_events_round_trip() -> None:
    """Verify SpellCast, AreaEffectExploded, and VFXAnimationFinished events are recorded."""
    repo = AggregateRepository(event_store=InMemoryEventStore(), aggregate_factory=BoardAggregate)
    sess_id = f"board-{uuid4().hex[:8]}"
    board_uuid = opaque_aggregate_id(sess_id, field="session_id")
    board = BoardAggregate(board_uuid)
    board.initialize_grid(cols=10, rows=10, session_id=sess_id)
    board.place_token("valeros", "Valeros", "pc", 2, 2, 40, True)

    anim_id, trajectory, affected_tokens, affected_cells, decal = board.cast_spell(
        spell_name="Chain Lightning",
        target_x=5,
        target_y=5,
        caster_token_id="valeros",
        spell_archetype="evocation",
        radius_ft=15,
        damage_type="lightning",
    )
    board.finish_vfx(anim_id, "Chain Lightning", 5, 5, 400)
    await repo.save(board)

    # Reload aggregate and verify event replay
    loaded_board = await repo.load(board_uuid)
    assert loaded_board is not None
    assert loaded_board.state.cols == 10
    assert len(loaded_board.state.active_decals) > 0


@pytest.mark.asyncio
async def test_unit_soundscape_aggregate_domain_round_trip():
    """Verify full domain event sourcing across mixins and event replay via AggregateRepository."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=SoundscapeAggregate)

    agg_id = uuid4()
    session_id = f"session-modular-{agg_id.hex[:8]}"

    # 1. Instantiate and apply domain commands across all mixins
    agg = SoundscapeAggregate(agg_id)

    # Stems mixin
    agg.record_track_change(
        session_id=session_id,
        track_id="track-dungeon-01",
        stem_profile="exploration",
        tension_score=20,
        crossfade_duration_ms=2000,
        active_stems=["ambient"],
    )
    assert agg.state.current_track_id == "track-dungeon-01"
    assert agg.state.stem_profile == "exploration"

    # Tension mixin
    agg.record_tension_update(
        session_id=session_id,
        tension_score=65,
        stem_profile="combat",
        combat_round=2,
        enemy_cr_balance=2.5,
        lowest_health_ratio=0.5,
    )
    assert agg.state.tension_score == 65
    assert agg.state.stem_profile == "combat"

    # Tension mixin mood override
    agg.record_stem_profile_overridden(session_id=session_id, mood="boss")
    assert agg.state.manual_override is True
    assert agg.state.stem_profile == "boss"

    # Foley mixin
    agg.record_cue(
        session_id=session_id,
        cue_id="cue-sword-clash",
        sound_url="https://s3.local/foley/sword.wav",
        volume_gain=0.9,
        duck_music=True,
    )
    assert len(agg.state.cues_history) == 1
    assert agg.state.cues_history[0]["cue_id"] == "cue-sword-clash"

    agg.record_ducking_engaged(session_id=session_id, reason="speech", duration_ms=0)
    assert agg.state.is_ducked is True
    assert agg.state.ducking_attenuation_db == -12.0
    agg.record_ducking_released(session_id=session_id)
    assert agg.state.is_ducked is False
    agg.record_ducking_engaged(session_id=session_id, reason="speech", duration_ms=0)
    agg.record_channel_volumes(session_id=session_id, channel_volumes={"melody": 0.3})
    agg.record_master_volume(session_id=session_id, master_volume=0.5)
    assert agg.state.channel_volumes["melody"] == 0.3
    assert agg.state.master_volume == 0.5

    # Leitmotif mixin
    agg.record_leitmotif_profile(
        session_id=session_id,
        character_id="char-valeros",
        character_name="Valeros",
        instrument_timbre="brass",
        tempo_multiplier=1.1,
    )
    assert "char-valeros" in agg.state.character_profiles

    agg.record_leitmotif_trigger(
        session_id=session_id,
        character_id="char-valeros",
        character_name="Valeros",
        motif_type="triumphant",
        instrument_timbre="brass",
    )
    assert agg.state.active_leitmotif is not None
    assert agg.state.active_leitmotif["character_id"] == "char-valeros"
    assert len(agg.state.leitmotif_history) == 1

    # Save uncommitted events into event store
    await repo.save(agg)

    # 2. Reconstitute aggregate from event store
    reconstituted = await repo.load(agg_id)
    assert reconstituted is not None
    assert reconstituted.state.current_track_id == "track-dungeon-01"
    assert reconstituted.state.tension_score == 65
    assert reconstituted.state.manual_override is True
    assert reconstituted.state.stem_profile == "boss"
    assert reconstituted.state.is_ducked is True
    assert len(reconstituted.state.cues_history) == 1
    assert "char-valeros" in reconstituted.state.character_profiles
    assert reconstituted.state.active_leitmotif["character_id"] == "char-valeros"
