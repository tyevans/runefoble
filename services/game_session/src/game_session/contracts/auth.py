"""SpiceDB Zanzibar authorization for mercenary contracts and escrow disbursement.

Governed by ADR-0001, ADR-0005, and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from runefoble_auth.spicedb import SpiceDBClient


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _check_perm(
    spicedb: SpiceDBClient, res: str, rid: str, perm: str, uid: str | None
) -> None:
    if uid and not await spicedb.check_permission(res, str(rid), perm, "user", uid):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{uid}' lacks '{perm}' on {res}:{rid}",
        )


async def check_bounty_view(spicedb: SpiceDBClient, sid: str, bid: str, uid: str | None) -> None:
    if uid:
        ok_b = bool(bid) and await spicedb.check_permission(
            "bounty_contract", str(bid), "view", "user", uid
        )
        ok_s = (
            await spicedb.check_permission("session", str(sid), "observe", "user", uid)
            or await spicedb.check_permission("session", str(sid), "participate", "user", uid)
            or await spicedb.check_permission("session", str(sid), "control", "user", uid)
        )
        if not (ok_b or ok_s):
            raise HTTPException(status_code=403, detail=f"User '{uid}' cannot view bounty '{bid}'")


async def check_bounty_post(spicedb: SpiceDBClient, sid: str, uid: str | None) -> None:
    if uid:
        ok_p = await spicedb.check_permission("session", str(sid), "participate", "user", uid)
        ok_c = await spicedb.check_permission("session", str(sid), "control", "user", uid)
        if not (ok_p or ok_c):
            raise HTTPException(
                status_code=403, detail=f"User '{uid}' cannot post bounty in session '{sid}'"
            )


async def check_bounty_claim(spicedb: SpiceDBClient, sid: str, bid: str, uid: str | None) -> None:
    if uid:
        ok_b = await spicedb.check_permission("bounty_contract", str(bid), "claim", "user", uid)
        ok_s = await spicedb.check_permission("session", str(sid), "participate", "user", uid)
        if not (ok_b or ok_s):
            raise HTTPException(status_code=403, detail=f"User '{uid}' cannot claim bounty '{bid}'")


async def check_bounty_disburse(
    spicedb: SpiceDBClient, bid: str, sid: str, uid: str | None
) -> None:
    if uid:
        ok_d = await spicedb.check_permission("bounty_contract", str(bid), "disburse", "user", uid)
        ok_m = await spicedb.check_permission("bounty_contract", str(bid), "manage", "user", uid)
        ok_f = await spicedb.check_permission("bounty_contract", str(bid), "fulfill", "user", uid)
        ok_c = await spicedb.check_permission("session", str(sid), "control", "user", uid)
        if not (ok_d or ok_m or ok_f or ok_c):
            raise HTTPException(
                status_code=403,
                detail=f"User '{uid}' lacks authorization to complete or disburse bounty '{bid}'",
            )


async def write_bounty_relationships(
    spicedb: SpiceDBClient, bid: str, sid: str, cid: str = "", uid: str | None = None
) -> None:
    await spicedb.write_relationship("bounty_contract", bid, "session", "session", sid)
    if cid:
        await spicedb.write_relationship("bounty_contract", bid, "campaign", "campaign", cid)
    if uid:
        await spicedb.write_relationship("bounty_contract", bid, "creator", "user", uid)


async def write_claimant_relationship(spicedb: SpiceDBClient, bid: str, uid: str | None) -> None:
    if uid:
        await spicedb.write_relationship("bounty_contract", bid, "claimant", "user", uid)
