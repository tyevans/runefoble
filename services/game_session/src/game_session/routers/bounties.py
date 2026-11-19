"""Bounty board router: post, query, claim, and complete mercenary contracts with escrow.

Governed by ADR-0001, ADR-0006, ADR-0007, and Hard Invariant 6 (< 150 lines).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from game_session.contracts.auth import (
    check_bounty_claim,
    check_bounty_disburse,
    check_bounty_post,
    check_bounty_view,
    write_bounty_relationships,
    write_claimant_relationship,
)
from game_session.contracts.child_indexes import SESSION_BOUNTIES, list_bounties_for_session
from game_session.contracts.engine import MercenaryBountyAggregate
from game_session.contracts.models import (
    ClaimBountyRequest,
    CompleteBountyRequest,
    PostBountyRequest,
)
from game_session.shared.child_index_queries import ChildIndexes, link_child
from game_session.shared.container_access import EventBus
from game_session.shared.identity import CallerId, get_principal
from game_session.shared.streams import STREAM_SESSION
from game_session.world.repositories import WorldRepos, WorldRepositories
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(dependencies=[Depends(get_principal)], prefix="/sessions", tags=["bounties"])


async def _load(repos: WorldRepositories, bid: UUID) -> MercenaryBountyAggregate:
    agg = await load_if_exists(repos.bounty_contracts, bid)
    if agg is None:
        raise HTTPException(status_code=404, detail="Bounty not found")
    return agg


def _err(fn, *a, **kw) -> Any:
    try:
        return fn(*a, **kw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{session_id}/contracts/bounties", status_code=201)
async def post_bounty(
    repos: WorldRepos,
    event_bus: EventBus,
    child_indexes: ChildIndexes,
    session_id: str,
    req: PostBountyRequest,
    caller_id: CallerId,
) -> dict[str, Any]:
    sid, spicedb = session_id, get_spicedb_client()
    await check_bounty_post(spicedb, str(sid), caller_id)
    bid = uuid4()
    agg = MercenaryBountyAggregate(bid)
    data = req.model_dump()
    cid = data.pop("campaign_id", req.campaign_id)
    agg.post_bounty(str(sid), cid, **data, poster_user_id=caller_id)
    events = list(agg.uncommitted_events)
    await repos.bounty_contracts.save(agg)
    if bus := event_bus.get():
        await publish_aggregate_events(bus, STREAM_SESSION, events)
    await link_child(child_indexes, SESSION_BOUNTIES, str(sid), str(bid))
    await write_bounty_relationships(spicedb, str(bid), str(sid), req.campaign_id, caller_id)
    return {"session_id": str(sid), "bounty": agg.state.model_dump()}


@router.get("/{session_id}/contracts/bounties")
async def list_bounties(
    repos: WorldRepos,
    child_indexes: ChildIndexes,
    caller_id: CallerId,
    session_id: str,
    status: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    min_gold: int | None = Query(default=None),
) -> dict[str, Any]:
    sid = session_id
    await check_bounty_view(get_spicedb_client(), str(sid), "", caller_id)
    repo, results = repos.bounty_contracts, []
    for bid_str in await list_bounties_for_session(child_indexes, str(sid)):
        agg = await load_if_exists(repo, UUID(bid_str))
        if agg is None:
            continue
        st = agg.state
        if (
            (status and st.status != status)
            or (target_type and st.target_type != target_type)
            or (min_gold is not None and st.escrow_gold < min_gold)
        ):
            continue
        results.append(st.model_dump())
    return {"session_id": str(sid), "bounties": results}


@router.get("/{session_id}/contracts/bounties/{bounty_id}")
async def get_bounty(
    repos: WorldRepos, session_id: str, bounty_id: str, caller_id: CallerId
) -> dict[str, Any]:
    sid, bid = session_id, parse_uuid(bounty_id, field="bounty_id")
    await check_bounty_view(get_spicedb_client(), str(sid), str(bid), caller_id)
    agg = await _load(repos, bid)
    return {"session_id": str(sid), "bounty": agg.state.model_dump()}


@router.post("/{session_id}/contracts/bounties/{bounty_id}/claim")
async def claim_bounty(
    repos: WorldRepos,
    event_bus: EventBus,
    caller_id: CallerId,
    session_id: str,
    bounty_id: str,
    req: ClaimBountyRequest,
) -> dict[str, Any]:
    sid, bid, spicedb = session_id, parse_uuid(bounty_id, field="bounty_id"), get_spicedb_client()
    await check_bounty_claim(spicedb, str(bid), caller_id)
    agg = await _load(repos, bid)
    _err(agg.claim_bounty, caller_id, req.claimant_campaign_id, req.claimant_party_name)
    events = list(agg.uncommitted_events)
    await repos.bounty_contracts.save(agg)
    if bus := event_bus.get():
        await publish_aggregate_events(bus, STREAM_SESSION, events)
    await write_claimant_relationship(spicedb, str(bid), caller_id)
    return {"session_id": str(sid), "bounty": agg.state.model_dump()}


@router.post("/{session_id}/contracts/bounties/{bounty_id}/complete")
async def complete_bounty(
    repos: WorldRepos,
    event_bus: EventBus,
    caller_id: CallerId,
    session_id: str,
    bounty_id: str,
    req: CompleteBountyRequest,
) -> dict[str, Any]:
    sid, bid = session_id, parse_uuid(bounty_id, field="bounty_id")
    await check_bounty_disburse(get_spicedb_client(), str(bid), caller_id)
    agg = await _load(repos, bid)
    payout = _err(agg.complete_bounty, proof=req.proof, disbursed_by=caller_id)
    events = list(agg.uncommitted_events)
    await repos.bounty_contracts.save(agg)
    if bus := event_bus.get():
        await publish_aggregate_events(bus, STREAM_SESSION, events)
    return {
        "session_id": str(sid),
        "bounty_id": str(bid),
        "status": "COMPLETED",
        "payout": payout,
        "escrow_locked": False,
        "bounty": agg.state.model_dump(),
    }
