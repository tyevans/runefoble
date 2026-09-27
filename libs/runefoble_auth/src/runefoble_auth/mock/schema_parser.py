"""Zed schema parsing and relationship graph representation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ZED_PATH = Path(__file__).resolve().parent.parent.parent.parent / "schema" / "runefoble.zed"


@dataclass
class RelationDef:
    name: str
    target_types: list[str] = field(default_factory=list)


@dataclass
class PermissionDef:
    name: str
    rules: list[str] = field(default_factory=list)


@dataclass
class ObjectDef:
    name: str
    relations: dict[str, RelationDef] = field(default_factory=dict)
    permissions: dict[str, PermissionDef] = field(default_factory=dict)


@dataclass
class SchemaGraph:
    definitions: dict[str, ObjectDef] = field(default_factory=dict)

    def get_permission_rules(self, object_type: str, permission: str) -> list[str]:
        obj = self.definitions.get(object_type)
        if not obj or permission not in obj.permissions:
            return []
        return obj.permissions[permission].rules

    def get_relation_types(self, object_type: str, relation: str) -> list[str]:
        obj = self.definitions.get(object_type)
        if not obj or relation not in obj.relations:
            return []
        return obj.relations[relation].target_types


def parse_zed_schema(schema_text: str) -> SchemaGraph:
    """Parse a Zanzibar Zed schema string into an ObjectDef/Relation graph."""
    graph = SchemaGraph()
    current_obj: ObjectDef | None = None

    for raw_line in schema_text.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        def_match = re.match(r"^definition\s+([a-zA-Z0-9_]+)\s*\{?$", line)
        if def_match:
            current_obj = ObjectDef(name=def_match.group(1))
            graph.definitions[current_obj.name] = current_obj
            continue
        if line == "}":
            current_obj = None
            continue
        if current_obj is None:
            continue
        rel_match = re.match(r"^relation\s+([a-zA-Z0-9_]+)\s*:\s*([a-zA-Z0-9_#|\s]+)$", line)
        if rel_match:
            r_name = rel_match.group(1)
            targets = [t.strip() for t in rel_match.group(2).split("|") if t.strip()]
            current_obj.relations[r_name] = RelationDef(name=r_name, target_types=targets)
            continue
        perm_match = re.match(r"^permission\s+([a-zA-Z0-9_]+)\s*=\s*(.+)$", line)
        if perm_match:
            p_name = perm_match.group(1)
            expr = perm_match.group(2).strip()
            rules = [r.strip() for r in expr.split("+") if r.strip() and r.strip() != "nil"]
            current_obj.permissions[p_name] = PermissionDef(name=p_name, rules=rules)
    return graph


def load_default_schema() -> SchemaGraph:
    """Load default Zanzibar schema from disk if available."""
    try:
        if DEFAULT_ZED_PATH.is_file():
            return parse_zed_schema(DEFAULT_ZED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Could not load default zed schema: %s", exc)
    return SchemaGraph()
