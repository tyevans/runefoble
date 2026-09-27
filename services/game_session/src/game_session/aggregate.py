"""Backward compatibility facade re-exporting GameSessionAggregate."""

from __future__ import annotations

from game_session.aggregate.aggregate import GameSessionAggregate
from game_session.aggregate.combat_handlers import CombatHandlersMixin
from game_session.aggregate.reaction_handlers import ReactionHandlersMixin
from game_session.aggregate.session_handlers import SessionHandlersMixin
from game_session.models import GameSessionState, ParticipantState

__all__ = [
    "CombatHandlersMixin",
    "GameSessionAggregate",
    "GameSessionState",
    "ParticipantState",
    "ReactionHandlersMixin",
    "SessionHandlersMixin",
]
