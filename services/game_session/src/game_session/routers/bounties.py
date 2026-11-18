"""Bounty board router: post, query, claim, and complete mercenary contracts with escrow.

Governed by ADR-0001, ADR-0006, ADR-0007, and Hard Invariant 6 (< 150 lines).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource import AggregateNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query
from game_session.contracts.auth import (
    _to_uuid,
    check_bounty_claim,
    check_bounty_disburse,
    check_bounty_post,
    check_bounty_view,
    write_bounty_relationships,
    write_claimant_relationship,
)
from game_session.contracts.engine import MercenaryBountyAggregate
from game_session.contracts.models import (
    ClaimBountyRequest,
    CompleteBountyRequest,
    PostBountyRequest,
)
from game_session.dependencies import (
    get_bounty_contract_repository,
    get_event_bus,
    get_session_bounties_index,
    get_spicedb_client,
)
from game_session.events import STREAM_SESSION
from game_session.settlement.auth.tokens import CallerId, get_caller_principal
from runefoble_platform.event_publish import publish_or_fail

router = APIRouter(
    dependencies=[Depends(get_caller_principal)], prefix="/sessions", tags=["bounties"]
)


async def _save_pub(agg: MercenaryBountyAggregate) -> None:
    events = list(agg.uncommitted_events)
    await get_bounty_contract_repository().save(agg)
    if bus := get_event_bus():
        for ev in events:
            await publish_or_fail(bus, STREAM_SESSION, ev)


async def _load(bid: UUID) -> MercenaryBountyAggregate:
    try:
        return await get_bounty_contract_repository().load(bid)
    except AggregateNotFoundError as e:
        raise HTTPException(status_code=404, detail="Bounty not found") from e


def _err(fn, *a, **kw) -> Any:
    try:
        return fn(*a, **kw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{session_id}/contracts/bounties", status_code=201)
async def post_bounty(
    session_id: str, req: PostBountyRequest, caller_id: CallerId
) -> dict[str, Any]:
    sid, spicedb = session_id, get_spicedb_client()
    await check_bounty_post(spicedb, str(sid), caller_id)
    bid = uuid4()
    agg = MercenaryBountyAggregate(bid)
    data = req.model_dump()
    cid = data.pop("campaign_id", req.campaign_id)
    agg.post_bounty(str(sid), cid, **data, poster_user_id=caller_id)
    await _save_pub(agg)
    get_session_bounties_index().setdefault(str(sid), []).append(str(bid))
    await write_bounty_relationships(spicedb, str(bid), str(sid), req.campaign_id, caller_id)
    return {"session_id": str(sid), "bounty": agg.state.model_dump()}


@router.get("/{session_id}/contracts/bounties")
async def list_bounties(
    caller_id: CallerId,
    session_id: str,
    status: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    min_gold: int | None = Query(default=None),
) -> dict[str, Any]:
    sid = session_id
    await check_bounty_view(get_spicedb_client(), str(sid), "", caller_id)
    repo, results = get_bounty_contract_repository(), []
    for bid_str in get_session_bounties_index().get(str(sid), []):
        try:
            st = (await repo.load(UUID(bid_str))).state
        except AggregateNotFoundError:
            continue
        if (
            (status and st.status != status)
            or (target_type and st.target_type != target_type)
            or (min_gold is not None and st.escrow_gold < min_gold)
        ):
            continue
        results.append(st.model_dump())
    return {"session_id": str(sid), "bounties": results}


@router.get("/{session_id}/contracts/bounties/{bounty_id}")
async def get_bounty(session_id: str, bounty_id: str, caller_id: CallerId) -> dict[str, Any]:
    sid, bid = session_id, _to_uuid(bounty_id)
    await check_bounty_view(get_spicedb_client(), str(sid), str(bid), caller_id)
    agg = await _load(bid)
    return {"session_id": str(sid), "bounty": agg.state.model_dump()}


@router.post("/{session_id}/contracts/bounties/{bounty_id}/claim")
async def claim_bounty(
    caller_id: CallerId,
    session_id: str,
    bounty_id: str,
    req: ClaimBountyRequest,
) -> dict[str, Any]:
    sid, bid, spicedb = session_id, _to_uuid(bounty_id), get_spicedb_client()
    await check_bounty_claim(spicedb, str(bid), caller_id)
    agg = await _load(bid)
    _err(agg.claim_bounty, caller_id, req.claimant_campaign_id, req.claimant_party_name)
    await _save_pub(agg)
    await write_claimant_relationship(spicedb, str(bid), caller_id)
    return {"session_id": str(sid), "bounty": agg.state.model_dump()}


@router.post("/{session_id}/contracts/bounties/{bounty_id}/complete")
async def complete_bounty(
    caller_id: CallerId,
    session_id: str,
    bounty_id: str,
    req: CompleteBountyRequest,
) -> dict[str, Any]:
    sid, bid = session_id, _to_uuid(bounty_id)
    await check_bounty_disburse(get_spicedb_client(), str(bid), caller_id)
    agg = await _load(bid)
    payout = _err(agg.complete_bounty, proof=req.proof, disbursed_by=caller_id)
    await _save_pub(agg)
    return {
        "session_id": str(sid),
        "bounty_id": str(bid),
        "status": "COMPLETED",
        "payout": payout,
        "escrow_locked": False,
        "bounty": agg.state.model_dump(),
    }
