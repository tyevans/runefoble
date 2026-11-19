"""SpiceDB checks and ownership writes for stored media assets (ADR-0001).

Every call fails closed. A SpiceDB error propagates as `AuthzError`, and the service maps it to
503 (`runefoble_auth.authz_http`). It never becomes a denial or a success. These checks cover the
Silo asset routes. The forge routes keep their own checks in `dependencies.py`.
"""

from __future__ import annotations

from runefoble_auth.permissions import require_subject
from runefoble_auth.port import SpiceDBPort


async def require_campaign_play(spicedb: SpiceDBPort, user_id: str, campaign_id: str) -> None:
    """Allow an asset to join a campaign only when the user can play in that campaign."""
    await require_subject(
        spicedb,
        "campaign",
        campaign_id,
        "play",
        user_id,
        detail=f"Permission denied: user '{user_id}' lacks 'play' on campaign '{campaign_id}'",
    )


async def require_asset_permission(
    spicedb: SpiceDBPort, user_id: str, asset_id: str, permission: str
) -> None:
    """Allow only when the schema grants `forged_asset.<permission>` on the asset to the user."""
    await require_subject(
        spicedb,
        "forged_asset",
        asset_id,
        permission,
        user_id,
        detail=f"Permission denied: user '{user_id}' lacks '{permission}' on asset '{asset_id}'",
    )


async def write_asset_ownership(
    spicedb: SpiceDBPort, asset_id: str, creator_id: str, campaign_id: str | None
) -> None:
    """Write the creator tuple and, when given, the campaign tuple for a new asset."""
    await spicedb.write_relationship("forged_asset", asset_id, "creator", "user", creator_id)
    if campaign_id:
        await spicedb.write_relationship(
            "forged_asset", asset_id, "campaign", "campaign", campaign_id
        )


async def revoke_asset_ownership(spicedb: SpiceDBPort, asset_id: str) -> None:
    """Remove every creator and campaign tuple of a deleted asset."""
    for relation in ("creator", "campaign"):
        for rel in await spicedb.read_relationships(
            resource_type="forged_asset", resource_id=asset_id, relation=relation
        ):
            await spicedb.delete_relationship(
                "forged_asset", asset_id, relation, rel.subject_type, rel.subject_id
            )
