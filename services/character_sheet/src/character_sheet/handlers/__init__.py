"""Modular command mutation handlers and event appliers for CharacterAggregate."""

from character_sheet.handlers.inventory import InventoryHandlerMixin
from character_sheet.handlers.spells import SpellsHandlerMixin
from character_sheet.handlers.vitals import VitalsHandlerMixin

__all__ = [
    "InventoryHandlerMixin",
    "SpellsHandlerMixin",
    "VitalsHandlerMixin",
]
