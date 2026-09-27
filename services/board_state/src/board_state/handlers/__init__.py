"""Modular command mutation handlers and event appliers for BoardAggregate."""

from board_state.handlers.actions import ActionsHandlerMixin
from board_state.handlers.fog import FogHandlerMixin
from board_state.handlers.physics import PhysicsHandlerMixin
from board_state.handlers.tokens import TokensHandlerMixin
from board_state.handlers.vfx import VFXHandlerMixin

__all__ = [
    "ActionsHandlerMixin",
    "FogHandlerMixin",
    "PhysicsHandlerMixin",
    "TokensHandlerMixin",
    "VFXHandlerMixin",
]
