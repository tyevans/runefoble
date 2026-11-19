"""SpiceDB Zanzibar object-level permission checks for Campaign Lore.

Every caller is the verified principal (TASK-0531). The helpers take a subject id, never
None. Each helper names one schema permission from `libs/runefoble_auth/schema/runefoble.zed`.
"""

from uuid import UUID

from runefoble_auth.permissions import check_subject
from runefoble_auth.port import SpiceDBPort


async def check_user_has_campaign_permission(
    user_id: str,
    campaign_id: UUID,
    permission: str,
    spicedb: SpiceDBPort,
) -> bool:
    """Return whether `user_id` holds `permission` on the campaign in the schema."""
    return await check_subject(spicedb, "campaign", str(campaign_id), permission, user_id)


async def check_user_can_read_secrets(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """Secret DM lore: `lore_document.read_secret` (campaign run_session)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "run_session", spicedb)


async def check_user_can_run_session(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """DM actions: lore ingest, handout forge, relic forge (campaign run_session)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "run_session", spicedb)


async def check_user_can_manage_campaign(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """Campaign administration: shared world linking (campaign manage, the owner)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "manage", spicedb)


async def check_user_can_view_campaign(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """Read access to campaign lore, atlas, and handouts (campaign view)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "view", spicedb)


async def check_user_can_play_campaign(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """Active play: handout interaction, atlas pins, discoveries, upgrades, notices (campaign play).

    The schema defines `play` as `run_session + player`, so one check covers DMs and players.
    """
    return await check_user_has_campaign_permission(user_id, campaign_id, "play", spicedb)


async def check_user_can_inspect_relic(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """Relic inspection and rune translation: `relic.inspect` (campaign view)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "view", spicedb)


async def check_user_can_interact_handout(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """Break seal and invisible-ink reveal: `diegetic_handout.interact` (campaign play)."""
    return await check_user_can_play_campaign(user_id, campaign_id, spicedb)


async def check_user_can_edit_atlas(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBPort,
) -> bool:
    """Layer toggle and territory writes: `atlas.edit` (campaign run_session)."""
    return await check_user_can_run_session(user_id, campaign_id, spicedb)
