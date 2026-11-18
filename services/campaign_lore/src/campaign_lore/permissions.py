"""SpiceDB Zanzibar object-level permission checks for Campaign Lore.

Every caller is the verified principal (TASK-0531). The helpers take a subject id, never
None. Each helper names one schema permission from `libs/runefoble_auth/schema/runefoble.zed`.
"""

from uuid import UUID

from runefoble_auth.spicedb import SpiceDBClient


async def check_user_has_campaign_permission(
    user_id: str,
    campaign_id: UUID,
    permission: str,
    spicedb: SpiceDBClient,
) -> bool:
    """Return whether `user_id` holds `permission` on the campaign in the schema."""
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission=permission,
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_read_secrets(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Secret DM lore: `lore_document.read_secret` (campaign run_session)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "run_session", spicedb)


async def check_user_can_run_session(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """DM actions: lore ingest, handout forge, relic forge (campaign run_session)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "run_session", spicedb)


async def check_user_can_manage_campaign(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Campaign administration: shared world linking (campaign manage, the owner)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "manage", spicedb)


async def check_user_can_view_campaign(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Read access to campaign lore, atlas, and handouts (campaign view)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "view", spicedb)


async def check_user_can_play_campaign(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Active play: handout interaction, atlas pins, discoveries, upgrades, notices (campaign play).

    The schema defines `play` as `run_session + player`, so one check covers DMs and players.
    """
    return await check_user_has_campaign_permission(user_id, campaign_id, "play", spicedb)


async def check_user_can_inspect_relic(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Relic inspection and rune translation: `relic.inspect` (campaign view)."""
    return await check_user_has_campaign_permission(user_id, campaign_id, "view", spicedb)


async def check_user_can_interact_handout(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Break seal and invisible-ink reveal: `diegetic_handout.interact` (campaign play)."""
    return await check_user_can_play_campaign(user_id, campaign_id, spicedb)


async def check_user_can_edit_atlas(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Layer toggle and territory writes: `atlas.edit` (campaign run_session)."""
    return await check_user_can_run_session(user_id, campaign_id, spicedb)
