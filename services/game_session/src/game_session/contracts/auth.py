"""SpiceDB Zanzibar authorization for mercenary bounty contracts and escrow disbursement.

Every check takes a verified caller id. No check passes without one. Permissions are the
names in libs/runefoble_auth/schema/runefoble.zed.

Governed by ADR-0001, ADR-0005, and Hard Invariant 1.
"""

from __future__ import annotations

from fastapi import HTTPException
from runefoble_auth.permissions import check_subject, require_subject
from runefoble_auth.port import SpiceDBPort


async def check_bounty_view(spicedb: SpiceDBPort, sid: str, bid: str, uid: str) -> None:
    """Allow a viewer of the bounty or an observer of its session."""
    ok_b = bool(bid) and await check_subject(spicedb, "bounty_contract", str(bid), "view", uid)
    ok_s = await check_subject(spicedb, "game_session", str(sid), "observe", uid)
    if not (ok_b or ok_s):
        raise HTTPException(status_code=403, detail=f"User '{uid}' cannot view bounty '{bid}'")


async def check_bounty_post(spicedb: SpiceDBPort, sid: str, uid: str) -> None:
    """Allow a session participant to post a bounty (session.participate is campaign.play)."""
    await require_subject(
        spicedb,
        "game_session",
        str(sid),
        "participate",
        uid,
        detail=f"User '{uid}' cannot post bounty in session '{sid}'",
    )


async def check_bounty_claim(spicedb: SpiceDBPort, bid: str, uid: str) -> None:
    """Allow a caller who holds bounty_contract.claim (play in the campaign or session)."""
    await require_subject(
        spicedb,
        "bounty_contract",
        str(bid),
        "claim",
        uid,
        detail=f"User '{uid}' cannot claim bounty '{bid}'",
    )


async def check_bounty_disburse(spicedb: SpiceDBPort, bid: str, uid: str) -> None:
    """Allow the creator, a campaign DM, or a session controller to disburse escrow."""
    await require_subject(
        spicedb,
        "bounty_contract",
        str(bid),
        "disburse",
        uid,
        detail=f"User '{uid}' lacks authorization to complete or disburse bounty '{bid}'",
    )


async def write_bounty_relationships(
    spicedb: SpiceDBPort, bid: str, sid: str, cid: str, uid: str
) -> None:
    await spicedb.write_relationship("bounty_contract", bid, "session", "game_session", sid)
    if cid:
        await spicedb.write_relationship("bounty_contract", bid, "campaign", "campaign", cid)
    await spicedb.write_relationship("bounty_contract", bid, "creator", "user", uid)


async def write_claimant_relationship(spicedb: SpiceDBPort, bid: str, uid: str) -> None:
    await spicedb.write_relationship("bounty_contract", bid, "claimant", "user", uid)
