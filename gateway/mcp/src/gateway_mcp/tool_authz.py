"""Schema permission checks for MCP tools (ADR-0001, TASK-0545).

Each mutating tool names one `Requirement`. The check reads the caller from the verified
MCP request, never from a tool argument. A missing caller, a denial, and a SpiceDB error
each stop the tool before it calls a service. A SpiceDB error is never a success.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp.exceptions import ToolError

from gateway_mcp.identity import caller_principal
from gateway_mcp.permissions import AuthorizationUnavailable, PermissionChecker

if TYPE_CHECKING:
    from gateway_mcp.dynamic.registry import DynamicToolRegistry


class ToolAuthzError(ToolError):
    """A tool call that the caller may not make, or that authorization cannot decide."""


@dataclass(frozen=True)
class Requirement:
    """One permission on one object. `via_campaign` checks the object's campaign instead."""

    resource_type: str
    resource_id: str
    permission: str
    via_campaign: str | None = None


def dm_action_on_character(character_id: str) -> Requirement:
    """A DM action on a character: `campaign.run_session` on the character's campaign."""
    return Requirement("character", character_id, "run_session", via_campaign="character")


def character_edit(character_id: str) -> Requirement:
    return Requirement("character", character_id, "edit")


def character_view(character_id: str) -> Requirement:
    """Read a character sheet: `character.view`, granted to the owner, the DM, and party members."""
    return Requirement("character", character_id, "view")


def token_move(token_id: str) -> Requirement:
    return Requirement("board_token", token_id, "move")


def session_control(session_id: str) -> Requirement:
    return Requirement("game_session", session_id, "control")


def tool_execute(tool_name: str) -> Requirement:
    return Requirement("mcp_tool", tool_name, "execute")


def require_caller_id(ctx: Any | None) -> str:
    """Return the verified user id of the MCP request, or refuse the call."""
    principal = caller_principal(ctx)
    if principal is None:
        raise ToolAuthzError("Authentication required: the request carries no verified caller.")
    return principal.user_id


async def check_requirement(
    permissions: PermissionChecker, user_id: str, requirement: Requirement
) -> None:
    """Raise `ToolAuthzError` unless the schema grants the requirement to the user."""
    permission = requirement.permission
    try:
        if requirement.via_campaign:
            campaign_ids = await permissions.campaign_ids(
                requirement.via_campaign, requirement.resource_id
            )
            targets = [("campaign", campaign_id) for campaign_id in campaign_ids]
        else:
            targets = [(requirement.resource_type, requirement.resource_id)]
        for resource_type, resource_id in targets:
            if await permissions.check(resource_type, resource_id, permission, user_id):
                return
    except AuthorizationUnavailable as exc:
        raise ToolAuthzError("Authorization service is unavailable. The call did not run.") from exc
    raise ToolAuthzError(
        f"Permission denied: user '{user_id}' lacks '{permission}' on "
        f"{requirement.resource_type} '{requirement.resource_id}'."
    )


async def authorize_tool_call(
    ctx: Any | None, permissions: PermissionChecker, requirement: Requirement
) -> str:
    """Check the requirement for the verified caller of `ctx`. Return the caller id."""
    user_id = require_caller_id(ctx)
    await check_requirement(permissions, user_id, requirement)
    return user_id


def step_requirement(
    registry: DynamicToolRegistry, tool_name: str, params: dict[str, Any]
) -> Requirement | None:
    """Return the permission one plan step needs, or None for a read-only static tool.

    A step that names a dynamic tool needs `mcp_tool.execute` on that tool. A step that
    names a static mutating tool needs the same permission as a direct call. A step with
    a missing id fails with a `ToolAuthzError`, so a plan never skips a check.
    """
    if registry.get_tool(tool_name) is not None:
        return tool_execute(tool_name)
    builders = _STEP_BUILDERS.get(tool_name)
    if builders is None:
        return None
    key, build = builders
    value = params.get(key)
    if not value:
        raise ToolAuthzError(
            f"Step '{tool_name}' needs '{key}' so that its permission can be checked."
        )
    return build(str(value))


_STEP_BUILDERS: dict[str, tuple[str, Any]] = {
    "apply_absentee_penalty": ("character_id", dm_action_on_character),
    "modify_character_hp": ("character_id", dm_action_on_character),
    "add_condition": ("character_id", dm_action_on_character),
    "apply_condition": ("character_id", dm_action_on_character),
    "cast_spell": ("character_id", character_edit),
    "move_board_token": ("token_id", token_move),
    "create_encounter": ("session_id", session_control),
}
