"""Tests for game_session spoken reactions and ready actions models."""

from __future__ import annotations

from uuid import UUID

import game_session.models.reactions as rx
from game_session.models import (
    DeclareReactionRequest,
    DeclareReactionResponse,
    EvaluateTriggersRequest,
    EvaluateTriggersResponse,
    GameSessionState,
    ReactionTransitionsMixin,
    ReadyActionRequest,
    ReadyActionResponse,
    ResolveReactionRequest,
    ResolveReactionResponse,
)


def test_reaction_exports_and_imports() -> None:
    """Verify re-exports and direct submodule imports for reaction models."""
    models = (
        ReadyActionRequest,
        ReadyActionResponse,
        ResolveReactionRequest,
        EvaluateTriggersRequest,
        EvaluateTriggersResponse,
        ReactionTransitionsMixin,
    )
    assert all(m is not None for m in models)
    assert rx.DeclareReactionRequest is DeclareReactionRequest
    assert rx.DeclareReactionResponse is DeclareReactionResponse
    assert rx.ResolveReactionResponse is ResolveReactionResponse


def test_reaction_state_transitions(initial_session_state: GameSessionState) -> None:
    """Verify turn pause on reaction declaration and resumption on resolution."""
    state = initial_session_state
    reaction_payload = {"reaction_id": "r-1", "reacting_combatant_id": "c1"}

    state = state.with_turn_paused_for_reaction(reaction_payload)
    assert state.turn_paused_for_reaction
    assert state.active_reaction == reaction_payload

    state = state.with_reaction_resolved("r-1", "shield")
    assert not state.turn_paused_for_reaction
    assert state.active_reaction is None


def test_ready_action_state_transitions(initial_session_state: GameSessionState) -> None:
    """Verify registration and triggering of conditional ready actions."""
    state = initial_session_state
    ready_payload = {
        "ready_action_id": "ra-1",
        "trigger_condition": "orc_steps_closer",
        "readied_action": "fire_arrow",
    }
    state = state.with_ready_action_registered(ready_payload)
    assert len(state.ready_actions) == 1

    state = state.with_ready_action_triggered("ra-1", {"trigger": "orc_moved"})
    assert len(state.ready_actions) == 0


def test_reaction_models_validation(
    session_id: UUID, initial_session_state: GameSessionState
) -> None:
    """Verify DTO validation, defaults, and response serialization."""
    dec_req = DeclareReactionRequest(reacting_combatant_id="c-1", trigger_phrase="When attacked")
    assert dec_req.timeout_seconds == 15.0

    dec_resp = DeclareReactionResponse(
        session_id=session_id, reaction_id="r-1", reacting_combatant_id="c-1"
    )
    assert dec_resp.status == "paused"

    res_resp = ResolveReactionResponse(
        session_id=session_id, reaction_id="r-1", session_state=initial_session_state
    )
    assert res_resp.resumed is True
