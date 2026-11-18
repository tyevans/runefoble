"""Every registered domain event follows one wire-name rule.

The wire name has the form runefoble.events.<bc>.<snake_case>. A retired class-name
identifier resolves to no event, because the platform keeps no aliases for old names.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import re

import pytest
import runefoble_events
from eventsource.domain.event_registry import default_registry, get_event_class_or_none
from runefoble_events.events import BattlemapForged
from runefoble_platform.event_deserializer import deserialize_event

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


@pytest.mark.parametrize(
    "retired_name", ["BattlemapForged", "FogRevealed", "ShroudReset", "BoardMoveEvent"]
)
def test_retired_short_name_does_not_deserialize(retired_name: str) -> None:
    fields = {"event_type": retired_name, "payload": json.dumps({"aggregate_id": "x"})}

    assert isinstance(deserialize_event(fields), dict)


def test_canonical_identifier_deserializes_to_the_event() -> None:
    payload = {
        "aggregate_id": "00000000-0000-4000-8000-000000000001",
        "asset_id": "asset-1",
        "creator_id": "user-1",
        "prompt": "crypt",
        "image_url": "https://example.test/crypt.png",
        "width_cells": 10,
        "height_cells": 10,
    }
    fields = {
        "event_type": "runefoble.events.asset.battlemap_forged",
        "payload": json.dumps(payload),
    }

    assert isinstance(deserialize_event(fields), BattlemapForged)


def test_no_registered_event_resolves_by_class_name() -> None:
    """Class names are never registry keys, so no retired short name still resolves."""
    leaked = [
        cls.__name__
        for cls in _load_all_registered_events()
        if cls.__module__.startswith("runefoble_events")
        and get_event_class_or_none(cls.__name__) is not None
    ]

    assert leaked == []
