"""SpiceDB checks and ownership writes for stored media assets (ADR-0001).

Every call fails closed. A SpiceDB error becomes a 503 response. It never becomes a
denial or a success. These checks cover the Silo asset routes. The forge routes keep
their own checks in `dependencies.py`.
"""

from __future__ import annotations

from fastapi import HTTPException
from runefoble_auth.errors import AuthzError
from runefoble_auth.spicedb import SpiceDBClient


def _unavailable(message: str) -> HTTPException:
    return HTTPException(
        status_code=503, detail={"error": "authorization_unavailable", "message": message}
    )


async def require_campaign_play(spicedb: SpiceDBClient, user_id: str, campaign_id: str) -> None:
    """Allow an asset to join a campaign only when the user can play in that campaign."""
    try:
        allowed = await spicedb.check_permission("campaign", campaign_id, "play", "user", user_id)
    except AuthzError as exc:
        raise _unavailable("Authorization service is unavailable.") from exc
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: user '{user_id}' lacks 'play' on campaign '{campaign_id}'",
        )


async def require_asset_manage(spicedb: SpiceDBClient, user_id: str, asset_id: str) -> None:
    """Allow only when the schema grants `forged_asset.manage` on the asset to the user."""
    try:
        allowed = await spicedb.check_permission(
            "forged_asset", asset_id, "manage", "user", user_id
        )
    except AuthzError as exc:
        raise _unavailable("Authorization service is unavailable.") from exc
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: user '{user_id}' lacks 'manage' on asset '{asset_id}'",
        )


async def write_asset_ownership(
    spicedb: SpiceDBClient, asset_id: str, creator_id: str, campaign_id: str | None
) -> None:
    """Write the creator tuple and, when given, the campaign tuple for a new asset."""
    try:
        await spicedb.write_relationship("forged_asset", asset_id, "creator", "user", creator_id)
        if campaign_id:
            await spicedb.write_relationship(
                "forged_asset", asset_id, "campaign", "campaign", campaign_id
            )
    except AuthzError as exc:
        raise _unavailable("Authorization service did not record the asset owner.") from exc


async def revoke_asset_ownership(spicedb: SpiceDBClient, asset_id: str) -> None:
    """Remove every creator and campaign tuple of a deleted asset."""
    try:
        for relation in ("creator", "campaign"):
            for rel in await spicedb.read_relationships(
                resource_type="forged_asset", resource_id=asset_id, relation=relation
            ):
                await spicedb.delete_relationship(
                    "forged_asset", asset_id, relation, rel.subject_type, rel.subject_id
                )
    except AuthzError as exc:
        raise _unavailable("Authorization service did not revoke the asset owner.") from exc
