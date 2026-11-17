"""Name contract: every type, relation, and permission name must exist in runefoble.zed.

Bounded contexts use `ACTION_PERMISSIONS` for domain actions. They never write a permission
name as a relation, and they never invent a role name as a grant.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

from functools import lru_cache

from runefoble_auth.errors import SchemaContractError
from runefoble_auth.schema_graph import (
    DEFAULT_ZED_PATH,
    SchemaGraph,
    parse_zed_schema,
)

# One mapping from a domain action to the (type, permission) pair that checks it.
ACTION_PERMISSIONS: dict[str, tuple[str, str]] = {
    "campaign.manage": ("campaign", "manage"),
    "campaign.run_session": ("campaign", "run_session"),
    "campaign.play": ("campaign", "play"),
    "campaign.view": ("campaign", "view"),
    "session.control": ("session", "control"),
    "session.participate": ("session", "participate"),
    "session.observe": ("session", "observe"),
    "character.edit": ("character", "edit"),
    "character.view": ("character", "view"),
    "character.delete": ("character", "delete"),
    "board.manage_traps": ("board", "manage_traps"),
    "board.view_secret_layer": ("board", "view_secret_layer"),
    "board.switch_map": ("board", "switch_map"),
    "board_token.move": ("board_token", "move"),
    "codex_entry.view": ("codex_entry", "view"),
    "codex_entry.edit": ("codex_entry", "edit"),
    "atlas.edit": ("atlas", "edit"),
    "atlas.place_pin": ("atlas", "place_pin"),
    "lore_document.read_secret": ("lore_document", "read_secret"),
    "homebrew_rule.manage": ("homebrew_rule", "manage"),
    "audience_poll.vote": ("audience_poll", "vote"),
    "audience_poll.approve": ("audience_poll", "approve"),
    "audience_poll.view": ("audience_poll", "view"),
}


@lru_cache(maxsize=1)
def load_contract() -> SchemaGraph:
    """Parse runefoble.zed once. A missing schema file raises."""
    return parse_zed_schema(DEFAULT_ZED_PATH.read_text(encoding="utf-8"))


def require_type(resource_type: str, graph: SchemaGraph | None = None) -> None:
    """Raise SchemaContractError when the schema does not define the type."""
    graph = graph or load_contract()
    if resource_type not in graph.definitions:
        raise SchemaContractError(f"Type '{resource_type}' is not defined in runefoble.zed")


def require_relation(resource_type: str, name: str, graph: SchemaGraph | None = None) -> None:
    """Raise SchemaContractError when `name` is not a relation of `resource_type`."""
    graph = graph or load_contract()
    require_type(resource_type, graph)
    if name not in graph.definitions[resource_type].relations:
        raise SchemaContractError(
            f"'{name}' is not a relation of '{resource_type}' in runefoble.zed"
        )


def require_permission(resource_type: str, name: str, graph: SchemaGraph | None = None) -> None:
    """Raise SchemaContractError when `name` is not a permission of `resource_type`."""
    graph = graph or load_contract()
    require_type(resource_type, graph)
    if name not in graph.definitions[resource_type].permissions:
        raise SchemaContractError(
            f"'{name}' is not a permission of '{resource_type}' in runefoble.zed"
        )


def require_subject_type(
    resource_type: str, relation: str, subject_type: str, graph: SchemaGraph | None = None
) -> None:
    """Raise SchemaContractError when the relation does not accept the subject type."""
    graph = graph or load_contract()
    require_relation(resource_type, relation, graph)
    allowed = graph.get_relation_types(resource_type, relation)
    if subject_type not in allowed:
        raise SchemaContractError(
            f"'{resource_type}#{relation}' accepts subjects {allowed}, not '{subject_type}'"
        )


def permission_for_action(action: str) -> tuple[str, str]:
    """Return the (type, permission) pair for a domain action.

    Raises:
        SchemaContractError: The action has no entry in ACTION_PERMISSIONS.
    """
    try:
        return ACTION_PERMISSIONS[action]
    except KeyError as exc:
        raise SchemaContractError(
            f"Action '{action}' has no permission in ACTION_PERMISSIONS"
        ) from exc
