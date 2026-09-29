"""Tests for game_session session, combat, and model structure invariants."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import game_session.models as models
import game_session.models.combat as combat_mod
import game_session.models.initiative as init_mod
import game_session.models.session as session_mod
import game_session.models.transitions as trans_mod
import game_session.models.turn_order as turn_mod
import pytest
from pydantic import ValidationError

from tests.test_game_session_models.conftest import FakeJoinedEvent


def test_session_and_combat_exports_and_imports() -> None:
    """Verify package re-exports and direct submodule imports for session and combat."""
    for req in ("CreateSessionRequest", "JoinSessionRequest", "LeaveSessionRequest"):
        assert getattr(models, req) is not None
    assert models.RollDiceRequest is not None and models.RollDiceResponse is not None
    assert issubclass(session_mod.GameSessionState, trans_mod.GameSessionTransitionsMixin)
    assert session_mod.GameSessionState is models.GameSessionState
    assert session_mod.ParticipantState is models.ParticipantState
    assert combat_mod.StartCombatRequest is models.StartCombatRequest
    assert turn_mod.NextTurnRequest is models.NextTurnRequest
    assert init_mod.InitiativeRollRequest is models.InitiativeRollRequest
    assert combat_mod.CombatStateResponse is models.CombatStateResponse
    assert models.CombatTransitionsMixin is not None


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


def test_model_files_line_count_invariants() -> None:
    """Verify model files adhere to file length limits."""
    models_dir = (
        Path(__file__).resolve().parents[2] / "services/game_session/src/game_session/models"
    )
    facade_file = models_dir.parent / "models.py"
    assert facade_file.exists() and len(facade_file.read_text().splitlines()) < 60

    budgets = {"settlement.py": 80, "reactions.py": 90}
    for sub_file in models_dir.glob("*.py"):
        limit = budgets.get(
            sub_file.name,
            100
            if sub_file.name in ("combat.py", "initiative.py", "session.py", "turn_order.py")
            else 120,
        )
        assert len(sub_file.read_text().splitlines()) < limit
