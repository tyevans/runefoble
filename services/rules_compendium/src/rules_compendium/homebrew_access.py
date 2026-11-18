"""Per-rule homebrew visibility for the rules compendium (ADR-0001, `homebrew_rule.view`)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient

from rules_compendium.dependencies import check_user_can_view_homebrew_rule
from rules_compendium.retrieval import CompendiumRetrievalEngine


async def visible_homebrew_rule_ids(
    user_id: str,
    campaign_id: UUID,
    engine: CompendiumRetrievalEngine,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> frozenset[str]:
    """Return the ids of campaign homebrew rules whose `homebrew_rule.view` check passes for the user.

    A rule the user cannot view is left out. A SpiceDB error propagates. It is never read as a denial.
    """
    visible: set[str] = set()
    for rule in engine.get_homebrew_by_campaign(campaign_id):
        rule_id = str(rule["rule_id"])
        if await check_user_can_view_homebrew_rule(user_id, rule_id, spicedb):
            visible.add(rule_id)
    return frozenset(visible)


async def visible_homebrew_monster(
    user_id: str,
    campaign_id: UUID,
    name: str,
    engine: CompendiumRetrievalEngine,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> dict[str, Any] | None:
    """Return a campaign homebrew monster by name when `homebrew_rule.view` passes. Else None.

    The caller cannot tell a hidden rule from a missing one.
    """
    candidate = engine.get_homebrew_monster(campaign_id, name)
    if candidate is None:
        return None
    if await check_user_can_view_homebrew_rule(user_id, str(candidate["monster_id"]), spicedb):
        return candidate
    return None
