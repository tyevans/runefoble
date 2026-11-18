"""Production name contract gate (Hard Invariant 1).

Every literal type, permission, and relation name that production code passes to a SpiceDB
call must exist in `libs/runefoble_auth/schema/runefoble.zed`. The test reads the real call
sites with `ast`. It does not match text. A name that the schema does not define fails here,
even when no unit test calls that path.

Checked call sites (string literal arguments only; a variable argument is not a literal):
- `check_permission(type, id, permission, subject_type, subject_id)`: permission on `type`.
- `write_relationship`, `touch_relationship`, `delete_relationship` (and the `*_tuple`
  helpers): relation on `type`, and the subject type must be accepted by that relation.
- `require_zanzibar_permission(permission, resource_type="campaign", ...)`: permission.
- `ACTION_PERMISSIONS` entries: (type, permission) pairs.

The gate has no allowlist. The sanity test keeps it from passing while it finds no call sites.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from runefoble_auth.contract import ACTION_PERMISSIONS, load_contract
from runefoble_auth.schema_graph import SchemaGraph

REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ROOTS = ("services", "gateway", "libs")
SKIPPED_PARTS = frozenset({"tests", "node_modules", ".venv", "__pycache__", ".worktrees"})

# Call name -> positional index of (resource type, permission or relation name).
CHECK_CALLS = {"check_permission": (0, 2)}
WRITE_CALLS = {
    "write_relationship": (0, 2),
    "touch_relationship": (0, 2),
    "delete_relationship": (0, 2),
    "write_relationship_tuple": (0, 2),
    "delete_relationship_tuple": (0, 2),
}
SUBJECT_TYPE_INDEX = 3
DEFAULT_ZANZIBAR_TYPE = "campaign"


@dataclass(frozen=True)
class NameUse:
    path: str
    line: int
    kind: str
    resource_type: str
    name: str
    subject_type: str | None = None

    def describe(self) -> str:
        return f"{self.path}:{self.line}: {self.kind} '{self.resource_type}#{self.name}'"


def _production_files() -> Iterator[Path]:
    for root in PRODUCTION_ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            if SKIPPED_PARTS.isdisjoint(path.relative_to(REPO_ROOT).parts):
                yield path


def _literal(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _argument(call: ast.Call, position: int | str) -> ast.expr | None:
    """Return the argument at a position, or the keyword argument with that name."""
    if isinstance(position, int):
        return call.args[position] if len(call.args) > position else None
    for keyword in call.keywords:
        if keyword.arg == position:
            return keyword.value
    return None


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _uses_in_call(path: str, call: ast.Call) -> Iterator[NameUse]:
    name = _call_name(call)
    line = call.lineno
    if name in CHECK_CALLS or name in WRITE_CALLS:
        type_idx, name_idx = (CHECK_CALLS if name in CHECK_CALLS else WRITE_CALLS)[name]
        resource_type = _literal(_argument(call, type_idx))
        member = _literal(_argument(call, name_idx))
        if resource_type is None or member is None:
            return
        subject_type = _literal(_argument(call, SUBJECT_TYPE_INDEX))
        kind = "permission" if name in CHECK_CALLS else "relation"
        yield NameUse(path, line, f"{name}:{kind}", resource_type, member, subject_type)
    elif name == "require_zanzibar_permission":
        permission = _literal(_argument(call, 0))
        if permission is None:
            return
        resource_type = _literal(_argument(call, "resource_type") or _argument(call, 1))
        yield NameUse(
            path, line, f"{name}:permission", resource_type or DEFAULT_ZANZIBAR_TYPE, permission
        )


def _uses_in_action_map(path: str, node: ast.Assign | ast.AnnAssign) -> Iterator[NameUse]:
    target = node.targets[0] if isinstance(node, ast.Assign) else node.target
    if not (isinstance(target, ast.Name) and target.id == "ACTION_PERMISSIONS"):
        return
    value = node.value
    if not isinstance(value, ast.Dict):
        return
    for entry in value.values:
        if isinstance(entry, ast.Tuple) and len(entry.elts) == 2:
            resource_type, permission = (_literal(elt) for elt in entry.elts)
            if resource_type is not None and permission is not None:
                yield NameUse(path, entry.lineno, "ACTION_PERMISSIONS", resource_type, permission)


def collect_name_uses() -> list[NameUse]:
    """Parse every production module and return each literal name use."""
    uses: list[NameUse] = []
    for file_path in _production_files():
        rel = file_path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                uses.extend(_uses_in_call(rel, node))
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                uses.extend(_uses_in_action_map(rel, node))
    return uses


def _mismatch(use: NameUse, graph: SchemaGraph) -> str | None:
    definition = graph.definitions.get(use.resource_type)
    if definition is None:
        return f"type '{use.resource_type}' is not defined"
    if use.kind.endswith("permission") or use.kind == "ACTION_PERMISSIONS":
        if use.name not in definition.permissions:
            return f"'{use.name}' is not a permission of '{use.resource_type}'"
        return None
    if use.name not in definition.relations:
        return f"'{use.name}' is not a relation of '{use.resource_type}'"
    if use.subject_type is not None:
        allowed = graph.get_relation_types(use.resource_type, use.name)
        if use.subject_type not in allowed:
            return f"'{use.resource_type}#{use.name}' accepts {allowed}, not '{use.subject_type}'"
    return None


def test_production_names_exist_in_schema() -> None:
    graph = load_contract()
    failures = []
    for use in collect_name_uses():
        problem = _mismatch(use, graph)
        if problem is not None:
            failures.append(f"{use.describe()} -> {problem}")
    assert not failures, "Names missing from runefoble.zed:\n" + "\n".join(sorted(failures))


def test_gate_finds_real_call_sites() -> None:
    """Guards against a vacuous pass: the scan must see the known SpiceDB call sites."""
    uses = collect_name_uses()
    kinds = {use.kind for use in uses}
    assert any(use.kind.startswith("check_permission") for use in uses)
    assert any(use.kind.startswith("write_relationship") for use in uses)
    assert "ACTION_PERMISSIONS" in kinds
    assert len(uses) >= 50


@pytest.mark.parametrize(("action", "pair"), sorted(ACTION_PERMISSIONS.items()))
def test_action_map_entry_is_a_schema_permission(action: str, pair: tuple[str, str]) -> None:
    resource_type, permission = pair
    assert permission in load_contract().definitions[resource_type].permissions, action
