"""Per-campaign permission flags for the caller. SpiceDB computes every flag (ADR-0001).

Each flag names the schema permission that the matching route guard checks. A true flag
means the route accepts the caller. The flag names are the App Shell contract (TASK-0644).
They are not schema names, so the mapping lives in one table here.
"""

from __future__ import annotations

from game_session.campaign.schemas import CampaignPermissionsResponse
from game_session.campaign.tuples import SpiceDB

# API flag -> schema permission on `campaign` that the matching route guard checks.
PERMISSION_FLAGS: dict[str, str] = {
    "view": "view",  # GET campaign, members, sessions
    "manage": "manage",  # PATCH campaign, remove member
    "invite": "run_session",  # POST invites
    "launch_session": "run_session",  # POST sessions
    "assign_roles": "manage",  # POST roles
}


async def campaign_permissions(
    spicedb: SpiceDB, campaign_id: str, user_id: str
) -> CampaignPermissionsResponse:
    """Check every flag for the caller. A non-member receives all false."""
    flags = {
        flag: await spicedb.check_permission("campaign", campaign_id, permission, "user", user_id)
        for flag, permission in PERMISSION_FLAGS.items()
    }
    return CampaignPermissionsResponse(**flags)
