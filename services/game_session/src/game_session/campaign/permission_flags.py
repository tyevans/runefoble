"""Per-campaign role and permission flags for the caller. SpiceDB computes each one (ADR-0001).

Each flag names the schema permission that the matching route guard checks. A true flag
means the route accepts the caller. The flag names are the App Shell contract (TASK-0644).
They are not schema names, so the mapping lives in one table here.

The role and the flags come from one set of granted schema permissions. A single campaign
reads that set with one concurrent check per distinct permission. A campaign list reads it
with one `LookupResources` per distinct permission, so the number of SpiceDB calls does not
grow with the number of campaigns (TASK-0907).
"""

from __future__ import annotations

import asyncio

from game_session.campaign.schemas import CampaignPermissionsResponse
from runefoble_auth.permissions import check_subject
from runefoble_auth.port import SpiceDBPort

# API flag -> schema permission on `campaign` that the matching route guard checks.
PERMISSION_FLAGS: dict[str, str] = {
    "view": "view",  # GET campaign, members, sessions
    "manage": "manage",  # PATCH campaign, remove member
    "invite": "run_session",  # POST invites
    "launch_session": "run_session",  # POST sessions
    "assign_roles": "manage",  # POST roles
}

# Schema permission -> role name, highest role first.
ROLE_CHECKS: tuple[tuple[str, str], ...] = (
    ("manage", "owner"),
    ("run_session", "dungeon_master"),
    ("play", "player"),
    ("view", "spectator"),
)

CAMPAIGN_PERMISSIONS: tuple[str, ...] = tuple(
    dict.fromkeys([*(p for p, _ in ROLE_CHECKS), *PERMISSION_FLAGS.values()])
)
"""Every distinct schema permission that the role and the flags need."""


def role_from(granted: frozenset[str]) -> str | None:
    """Return the highest role that the granted permissions give, or None."""
    return next((role for permission, role in ROLE_CHECKS if permission in granted), None)


def flags_from(granted: frozenset[str]) -> CampaignPermissionsResponse:
    """Return the App Shell flags for the granted permissions. No grant gives all false."""
    return CampaignPermissionsResponse(
        **{flag: permission in granted for flag, permission in PERMISSION_FLAGS.items()}
    )


async def granted_permissions(
    spicedb: SpiceDBPort, campaign_id: str, user_id: str
) -> frozenset[str]:
    """Check each distinct permission on one campaign concurrently. A failure raises."""
    results = await asyncio.gather(
        *(
            check_subject(spicedb, "campaign", campaign_id, permission, user_id)
            for permission in CAMPAIGN_PERMISSIONS
        )
    )
    return frozenset(p for p, ok in zip(CAMPAIGN_PERMISSIONS, results, strict=True) if ok)


async def granted_by_campaign(spicedb: SpiceDBPort, user_id: str) -> dict[str, frozenset[str]]:
    """Return the granted permissions per campaign id, from one lookup per permission.

    A campaign without `view` is absent. A SpiceDB failure raises.
    """
    found = await asyncio.gather(
        *(
            spicedb.lookup_resources("campaign", permission, "user", user_id)
            for permission in CAMPAIGN_PERMISSIONS
        )
    )
    by_campaign: dict[str, set[str]] = {}
    for permission, campaign_ids in zip(CAMPAIGN_PERMISSIONS, found, strict=True):
        for campaign_id in campaign_ids:
            by_campaign.setdefault(campaign_id, set()).add(permission)
    return {cid: frozenset(perms) for cid, perms in by_campaign.items() if "view" in perms}
