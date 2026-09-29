"""Tests for game_session absentee autopilot and mid-session hot-swap models."""

from __future__ import annotations

from uuid import UUID

from game_session.models import (
    AutoPilotRequest,
    AutoPilotResponse,
    GameSessionState,
    HotSwapRequest,
    HotSwapResponse,
)
from the_watcher.watcher_ai import StandInAction

from tests.test_game_session_models.conftest import FakeJoinedEvent


def test_autopilot_and_hotswap_exports() -> None:
    """Verify autopilot and hot-swap DTO re-exports."""
    models = (AutoPilotRequest, AutoPilotResponse, HotSwapRequest, HotSwapResponse)
    assert all(m is not None for m in models)


def test_absentee_stand_in_lifecycle(
    initial_session_state: GameSessionState, character_id: UUID
) -> None:
    """Verify absentee stand-in takeover and stand-in action recording."""
    state = initial_session_state.with_player_joined(FakeJoinedEvent(character_id))
    state = state.without_player_presence("player-1")
    assert not state.participants["player-1"].is_present
    assert state.participants["player-1"].is_stand_in_active

    state = state.with_stand_in_action(
        {
            "character_name": "Kaelen",
            "action_type": "ranged_attack",
            "dialogue": "Watch your flank!",
            "penalties_applied": [],
            "flavor_text": "Shoots an arrow with precision.",
        }
    )
    assert len(state.stand_in_actions) == 1


def test_hotswap_control_transfer_transition(
    initial_session_state: GameSessionState, character_id: UUID
) -> None:
    """Verify returning player hot-swap takeover removes stand-in status."""
    state = initial_session_state.with_player_joined(FakeJoinedEvent(character_id))
    state = state.without_player_presence("player-1")
    state = state.with_character_control_transferred("player-1", character_id)
    assert state.participants["player-1"].is_present
    assert not state.participants["player-1"].is_stand_in_active


def test_autopilot_and_hotswap_model_validation(
    session_id: UUID, character_id: UUID, initial_session_state: GameSessionState
) -> None:
    """Verify DTO validation, defaults, and controller assignments."""
    action = StandInAction(
        character_name="Kaelen",
        action_type="dash",
        action_description="Dashes 30 feet forward.",
        dialogue="Covering ground!",
        penalties_applied=["foolishness"],
        flavor_text="Dashes forward.",
    )
    ap_resp = AutoPilotResponse(
        session_id=session_id,
        current_turn=1,
        action=action,
        stand_in_action=action,
        session_state=initial_session_state,
    )
    assert ap_resp.session_id == session_id and ap_resp.action.action_type == "dash"

    hs_resp = HotSwapResponse(
        session_id=session_id,
        character_id=character_id,
        player_id="p-1",
        current_turn=1,
        in_combat=False,
        combat_round=1,
        combat_active_id=None,
        session_state=initial_session_state,
    )
    assert hs_resp.new_controller == "player"
