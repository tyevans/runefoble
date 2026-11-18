"""Tests for game_session session, combat, and model structure invariants."""

from __future__ import annotations

from uuid import UUID

import game_session.models as models
import pytest
from pydantic import ValidationError

from tests.test_game_session_models.conftest import FakeJoinedEvent


def test_session_lifecycle_and_validation(
    initial_session_state: models.GameSessionState, character_id: UUID
) -> None:
    """Verify session creation, participant joining, turn advancing, and DTO validation."""
    state = initial_session_state
    assert state.status == "lobby" and state.current_turn == 1 and not state.in_combat

    state = state.with_player_joined(FakeJoinedEvent(character_id))
    assert "player-1" in state.participants
    participant = state.participants["player-1"]
    assert participant.character_name == "Kaelen" and participant.is_present
    assert not participant.is_stand_in_active

    state = state.with_turn_advanced(2, character_id)
    assert state.current_turn == 2 and state.active_character_id == character_id

    with pytest.raises(ValidationError):
        models.CreateSessionRequest()


def test_combat_transitions(initial_session_state: models.GameSessionState) -> None:
    """Verify combat round transitions and turn order progression."""
    state = initial_session_state
    order = [
        {"combatant_id": "c1", "initiative_score": 18.0},
        {"combatant_id": "c2", "initiative_score": 12.0},
    ]

    state = state.with_combat_started(1, order)
    assert state.in_combat and state.combat_round == 1 and state.combat_active_id == "c1"

    state = state.with_initiative_turn_advanced(1, "c2")
    assert state.combat_active_id == "c2"

    state = state.with_combat_ended()
    assert not state.in_combat and state.combat_active_id is None
