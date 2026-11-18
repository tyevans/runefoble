"""Per-rule homebrew visibility for the rules compendium (ADR-0001, `homebrew_rule.view`)."""

from __future__ import annotations

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
