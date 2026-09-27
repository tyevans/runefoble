"""Tests verifying modular decomposition and backward compatibility of game_session models.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 500 lines, target < 120 lines per model submodule)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import game_session.models as models_pkg
import pytest
from game_session.models import (
    DEFAULT_FACILITIES,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
    AutoPilotRequest,
    AutoPilotResponse,
    CharterSettlementRequest,
    ClaimRestBoonRequest,
    CombatStateResponse,
    CombatTransitionsMixin,
    CreateSessionRequest,
    DeclareReactionRequest,
    DeclareReactionResponse,
    EvaluateTriggersRequest,
    EvaluateTriggersResponse,
    GameSessionState,
    GameSessionTransitionsMixin,
    HotSwapRequest,
    HotSwapResponse,
    InitiativeRollRequest,
    JoinSessionRequest,
    LeaveSessionRequest,
    NextTurnRequest,
    ParticipantState,
    ReactionTransitionsMixin,
    ReadyActionRequest,
    ReadyActionResponse,
    ResolveReactionRequest,
    ResolveReactionResponse,
    RollDiceRequest,
    RollDiceResponse,
    SettlementState,
    StartCombatRequest,
    UpgradeFacilityRequest,
)
from pydantic import ValidationError
from the_watcher.watcher_ai import StandInAction


def test_package_facade_and_backward_compatibility() -> None:
    """Verify that all domain models, schemas, and mixins are cleanly re-exported."""
    assert models_pkg is not None
    assert GameSessionState is not None
    assert ParticipantState is not None
    assert GameSessionTransitionsMixin is not None
    assert CombatTransitionsMixin is not None
    assert ReactionTransitionsMixin is not None

    # Verify session schemas
    assert CreateSessionRequest is not None
    assert JoinSessionRequest is not None
    assert LeaveSessionRequest is not None
    assert AutoPilotRequest is not None
    assert AutoPilotResponse is not None
    assert HotSwapRequest is not None
    assert HotSwapResponse is not None

    # Verify combat & initiative schemas
    assert StartCombatRequest is not None
    assert InitiativeRollRequest is not None
    assert NextTurnRequest is not None
    assert CombatStateResponse is not None
    assert RollDiceRequest is not None
    assert RollDiceResponse is not None

    # Verify reaction schemas
    assert DeclareReactionRequest is not None
    assert DeclareReactionResponse is not None
    assert ReadyActionRequest is not None
    assert ReadyActionResponse is not None
    assert ResolveReactionRequest is not None
    assert ResolveReactionResponse is not None
    assert EvaluateTriggersRequest is not None
    assert EvaluateTriggersResponse is not None

    # Verify settlement schemas
    assert SettlementState is not None
    assert CharterSettlementRequest is not None
    assert UpgradeFacilityRequest is not None
    assert ClaimRestBoonRequest is not None
    assert DEFAULT_FACILITIES is not None
    assert FACILITY_REST_BOONS is not None
    assert FACILITY_TIER_NAMES is not None


def test_submodule_direct_imports() -> None:
    """Verify that models are directly importable from their domain submodules."""
    from game_session.models.combat import CombatStateResponse as CombatStateResp
    from game_session.models.combat import StartCombatRequest as StartCombatReq
    from game_session.models.initiative import InitiativeRollRequest as InitRollReq
    from game_session.models.reactions import DeclareReactionRequest as DeclReactReq
    from game_session.models.reactions import ResolveReactionResponse as ResolvReactResp
    from game_session.models.session import GameSessionState as GSS
    from game_session.models.session import ParticipantState as PartState
    from game_session.models.settlement import SettlementState as SettlState
    from game_session.models.transitions import GameSessionTransitionsMixin as GSTM
    from game_session.models.turn_order import NextTurnRequest as NextTurnReq

    assert issubclass(GSS, GSTM)
    assert GSS is GameSessionState
    assert PartState is ParticipantState
    assert SettlState is SettlementState
    assert StartCombatReq is StartCombatRequest
    assert NextTurnReq is NextTurnRequest
    assert InitRollReq is InitiativeRollRequest
    assert CombatStateResp is CombatStateResponse
    assert DeclReactReq is DeclareReactionRequest
    assert ResolvReactResp is ResolveReactionResponse


def test_model_files_line_count_invariants() -> None:
    """Verify all model files strictly adhere to Hard Invariant 6 (< 120 lines budget)."""
    models_dir = (
        Path(__file__).resolve().parent.parent
        / "services"
        / "game_session"
        / "src"
        / "game_session"
        / "models"
    )
    facade_file = models_dir.parent / "models.py"

    assert facade_file.exists(), f"Facade file {facade_file} does not exist"
    facade_lines = len(facade_file.read_text().splitlines())
    assert facade_lines < 60, f"Facade {facade_file} has {facade_lines} lines (expected < 60)"

    expected_submodules = {
        "combat.py": 100,
        "combat_transitions.py": 120,
        "initiative.py": 100,
        "__init__.py": 120,
        "reactions.py": 90,
        "reaction_transitions.py": 120,
        "session.py": 100,
        "settlement.py": 80,
        "stand_in_transitions.py": 120,
        "transitions.py": 120,
        "turn_order.py": 100,
    }

    for sub_filename, max_lines in expected_submodules.items():
        sub_file = models_dir / sub_filename
        assert sub_file.exists(), f"Submodule file {sub_file} does not exist"
        lines = len(sub_file.read_text().splitlines())
        assert lines < max_lines, (
            f"{sub_filename} has {lines} lines, exceeding limit of {max_lines}"
        )


def test_game_session_state_transitions_blackbox() -> None:
    """Verify GameSessionState transitions maintain valid domain state."""
    session_id = uuid4()
    campaign_id = uuid4()
    char_id = uuid4()

    state = GameSessionState.initial(
        session_id=session_id,
        campaign_id=campaign_id,
        title="Tomb of the Star-Eater",
        dm_id="the_watcher",
    )
    assert state.status == "lobby"
    assert state.current_turn == 1
    assert not state.in_combat

    # Participant join
    class FakeJoinedEvent:
        player_id = "player-1"
        character_id = char_id
        character_name = "Kaelen"
        character_class = "Ranger"

    state = state.with_player_joined(FakeJoinedEvent())
    assert "player-1" in state.participants
    participant = state.participants["player-1"]
    assert participant.character_name == "Kaelen"
    assert participant.is_present
    assert not participant.is_stand_in_active

    # Turn advancement
    state = state.with_turn_advanced(2, char_id)
    assert state.current_turn == 2
    assert state.active_character_id == char_id

    # Absentee stand-in
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

    # Hot-swap control transfer
    state = state.with_character_control_transferred("player-1", char_id)
    assert state.participants["player-1"].is_present
    assert not state.participants["player-1"].is_stand_in_active

    # Combat lifecycle
    order = [
        {"combatant_id": "c1", "initiative_score": 18.0},
        {"combatant_id": "c2", "initiative_score": 12.0},
    ]
    state = state.with_combat_started(1, order)
    assert state.in_combat
    assert state.combat_round == 1
    assert state.combat_active_id == "c1"

    state = state.with_initiative_turn_advanced(1, "c2")
    assert state.combat_active_id == "c2"

    # Spoken reactions
    reaction_payload = {"reaction_id": "r-1", "reacting_combatant_id": "c1"}
    state = state.with_turn_paused_for_reaction(reaction_payload)
    assert state.turn_paused_for_reaction
    assert state.active_reaction == reaction_payload

    state = state.with_reaction_resolved("r-1", "shield")
    assert not state.turn_paused_for_reaction
    assert state.active_reaction is None

    # Ready actions
    ready_payload = {
        "ready_action_id": "ra-1",
        "trigger_condition": "orc_steps_closer",
        "readied_action": "fire_arrow",
    }
    state = state.with_ready_action_registered(ready_payload)
    assert len(state.ready_actions) == 1

    state = state.with_ready_action_triggered("ra-1", {"trigger": "orc_moved"})
    assert len(state.ready_actions) == 0

    state = state.with_combat_ended()
    assert not state.in_combat
    assert state.combat_active_id is None


def test_model_serialization_and_validation() -> None:
    """Verify DTO validation, defaults, and serializability."""
    session_id = uuid4()
    char_id = uuid4()

    state = GameSessionState.initial(
        session_id=session_id,
        campaign_id=uuid4(),
        title="Session Test",
        dm_id="dm_1",
    )

    action = StandInAction(
        character_name="Kaelen",
        action_type="dash",
        action_description="Dashes 30 feet forward.",
        dialogue="Covering ground!",
        penalties_applied=["foolishness"],
        flavor_text="Dashes forward.",
    )

    # AutoPilotResponse validation
    ap_resp = AutoPilotResponse(
        session_id=session_id,
        current_turn=1,
        action=action,
        stand_in_action=action,
        session_state=state,
    )
    assert ap_resp.session_id == session_id
    assert ap_resp.action.action_type == "dash"

    # HotSwapResponse validation
    hs_resp = HotSwapResponse(
        session_id=session_id,
        character_id=char_id,
        player_id="p-1",
        current_turn=1,
        in_combat=False,
        combat_round=1,
        combat_active_id=None,
        session_state=state,
    )
    assert hs_resp.new_controller == "player"

    # Reaction schemas validation
    dec_req = DeclareReactionRequest(
        reacting_combatant_id="c-1",
        trigger_phrase="When attacked",
    )
    assert dec_req.timeout_seconds == 15.0

    dec_resp = DeclareReactionResponse(
        session_id=session_id,
        reaction_id="r-1",
        reacting_combatant_id="c-1",
    )
    assert dec_resp.status == "paused"

    res_resp = ResolveReactionResponse(
        session_id=session_id,
        reaction_id="r-1",
        session_state=state,
    )
    assert res_resp.resumed is True

    # Settlement schemas validation
    settlement = SettlementState(
        settlement_id="haven-1",
        name="Wolfstone Outpost",
        settlement_type="outpost",
    )
    assert settlement.level == 1
    assert "workshop" in settlement.facilities

    # Invalid payload validation
    with pytest.raises(ValidationError):
        CreateSessionRequest()  # missing campaign_id
