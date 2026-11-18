"""SpiceDB Zanzibar authorization for mercenary bounty contracts and escrow disbursement.

Every check takes a verified caller id. No check passes without one. Permissions are the
names in libs/runefoble_auth/schema/runefoble.zed.

Governed by ADR-0001, ADR-0005, and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient

Spicedb = SpiceDBClient | MockSpiceDBClient


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def check_bounty_view(spicedb: Spicedb, sid: str, bid: str, uid: str) -> None:
    """Allow a viewer of the bounty or an observer of its session."""
    ok_b = bool(bid) and await spicedb.check_permission(
        "bounty_contract", str(bid), "view", "user", uid
    )
    ok_s = await spicedb.check_permission("session", str(sid), "observe", "user", uid)
    if not (ok_b or ok_s):
        raise HTTPException(status_code=403, detail=f"User '{uid}' cannot view bounty '{bid}'")


async def check_bounty_post(spicedb: Spicedb, sid: str, uid: str) -> None:
    """Allow a session participant to post a bounty (session.participate is campaign.play)."""
    if not await spicedb.check_permission("session", str(sid), "participate", "user", uid):
        raise HTTPException(
            status_code=403, detail=f"User '{uid}' cannot post bounty in session '{sid}'"
        )


async def check_bounty_claim(spicedb: Spicedb, bid: str, uid: str) -> None:
    """Allow a caller who holds bounty_contract.claim (play in the campaign or session)."""
    if not await spicedb.check_permission("bounty_contract", str(bid), "claim", "user", uid):
        raise HTTPException(status_code=403, detail=f"User '{uid}' cannot claim bounty '{bid}'")


async def check_bounty_disburse(spicedb: Spicedb, bid: str, uid: str) -> None:
    """Allow the creator, a campaign DM, or a session controller to disburse escrow."""
    if not await spicedb.check_permission("bounty_contract", str(bid), "disburse", "user", uid):
        raise HTTPException(
            status_code=403,
            detail=f"User '{uid}' lacks authorization to complete or disburse bounty '{bid}'",
        )


async def write_bounty_relationships(
    spicedb: Spicedb, bid: str, sid: str, cid: str, uid: str
) -> None:
    await spicedb.write_relationship("bounty_contract", bid, "session", "session", sid)
    if cid:
        await spicedb.write_relationship("bounty_contract", bid, "campaign", "campaign", cid)
    await spicedb.write_relationship("bounty_contract", bid, "creator", "user", uid)


async def write_claimant_relationship(spicedb: Spicedb, bid: str, uid: str) -> None:
    await spicedb.write_relationship("bounty_contract", bid, "claimant", "user", uid)
