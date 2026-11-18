"""Every registered domain event follows one wire-name rule.

The wire name has the form runefoble.events.<bc>.<snake_case>. A retired class-name
identifier resolves to no event, because the platform keeps no aliases for old names.
"""

from __future__ import annotations

import importlib
import pkgutil
import re

import runefoble_events
from eventsource.domain.event_registry import default_registry, get_event_class_or_none

WIRE_NAME_RULE = re.compile(r"^runefoble\.events\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


def _load_all_registered_events() -> list[type]:
    for module in pkgutil.walk_packages(runefoble_events.__path__, runefoble_events.__name__ + "."):
        importlib.import_module(module.name)
    return list(default_registry.list_classes())


def test_every_registered_event_uses_the_wire_name_rule() -> None:
    names = {
        cls.__name__: cls.event_type_name()
        for cls in _load_all_registered_events()
        if cls.__module__.startswith("runefoble_events")
    }
    violations = {cls: name for cls, name in names.items() if not WIRE_NAME_RULE.match(name)}

    assert violations == {}


def test_retired_class_name_identifiers_resolve_to_no_event() -> None:
    assert get_event_class_or_none("CharacterCreated") is None
    assert get_event_class_or_none("TokenMoved") is None
    assert get_event_class_or_none("runefoble.events.character.CharacterCreated") is None
