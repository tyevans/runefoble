"""Caravan notice board router: post, list, and view contracts.

Part of TASK-0147 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from game_session.caravan import CaravanContractAggregate
from game_session.child_index import ChildIndexKind
from game_session.dependencies import get_caravan_contract_repository
from game_session.queries import link_child, list_world_contracts_for_world
from game_session.routers.caravan_contracts.auth import (
    _check_high_tier_auth,
    _publish,
)
from game_session.settlement.auth.tokens import CallerId, get_principal
from game_session.west_marches_models import PostCaravanContractRequest
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import require_subject
from runefoble_platform.aggregate_loading import load_if_exists, load_or_404
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(
    dependencies=[Depends(get_principal)],
    prefix="/api/v1/shared-worlds",
    tags=["caravan-contracts"],
)


@router.post("/{shared_world_id}/caravans/contracts", status_code=201)
async def post_caravan_contract(
    caller_id: CallerId,
    shared_world_id: str,
    req: PostCaravanContractRequest,
) -> dict[str, Any]:
    """Post an asynchronous mercenary escort contract to the shared world notice board."""
    wid = parse_uuid(shared_world_id, field="shared_world_id")
    spicedb = get_spicedb_client()
    await require_subject(spicedb, "shared_world", str(wid), "trade", caller_id)
    await _check_high_tier_auth(
        spicedb, str(wid), req.posted_by_campaign_id, req.route_risk_level, caller_id
    )

    contract_id = uuid4()
    contract_repo = get_caravan_contract_repository()
    contract = CaravanContractAggregate(contract_id)

    cid = contract.post_contract(
        shared_world_id=wid,
        origin_outpost=req.origin_outpost,
        destination_outpost=req.destination_outpost,
        cargo=req.cargo,
        cargo_value=req.cargo_value,
        posted_by_campaign_id=req.posted_by_campaign_id,
        route_risk_level=req.route_risk_level,
        transit_stages=req.transit_stages,
        escort_collateral=req.escort_collateral,
        reward_gold=req.reward_gold,
        reward_reputation=req.reward_reputation,
        poster_user_id=caller_id,
        expires_in_turns=req.expires_in_turns,
    )
    events = list(contract.uncommitted_events)
    await contract_repo.save(contract)

    # Register in world notice board index and write Zanzibar relations
    await link_child(ChildIndexKind.WORLD_CONTRACTS, str(wid), cid)
    await spicedb.write_relationship(
        "caravan_contract", cid, "shared_world", "shared_world", str(wid)
    )
    await spicedb.write_relationship("caravan_contract", cid, "poster", "user", caller_id)

    await _publish(events)
    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


@router.get("/{shared_world_id}/caravans/contracts")
async def list_caravan_contracts(
    caller_id: CallerId,
    shared_world_id: str,
    status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    destination: str | None = Query(default=None),
    min_reward: int | None = Query(default=None),
) -> dict[str, Any]:
    """Query available notice board contracts applying optional frontier filters."""
    wid = parse_uuid(shared_world_id, field="shared_world_id")
    spicedb = get_spicedb_client()
    await require_subject(spicedb, "shared_world", str(wid), "view", caller_id)

    contract_repo = get_caravan_contract_repository()
    cids = await list_world_contracts_for_world(str(wid))
    contracts: list[dict[str, Any]] = []

    for c_id in cids:
        c_agg = await load_if_exists(contract_repo, UUID(c_id))
        if c_agg is None:
            continue
        c_state = c_agg.state
        if (
            (status and c_state.status != status)
            or (risk_level and c_state.route_risk_level.lower() != risk_level.lower())
            or (destination and c_state.destination_outpost.lower() != destination.lower())
            or (min_reward is not None and c_state.reward_gold < min_reward)
        ):
            continue
        contracts.append(c_state.model_dump())

    return {"shared_world_id": str(wid), "contracts": contracts}


@router.get("/{shared_world_id}/caravans/contracts/{contract_id}")
async def get_caravan_contract(
    caller_id: CallerId,
    shared_world_id: str,
    contract_id: str,
) -> dict[str, Any]:
    """Retrieve details and manifest for a specific caravan escort contract."""
    wid, cid = (
        parse_uuid(shared_world_id, field="shared_world_id"),
        parse_uuid(contract_id, field="contract_id"),
    )
    spicedb = get_spicedb_client()
    await require_subject(spicedb, "caravan_contract", str(cid), "view", caller_id)

    contract = await load_or_404(get_caravan_contract_repository(), cid, "Contract not found")

    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


__all__ = ["get_caravan_contract", "list_caravan_contracts", "post_caravan_contract", "router"]
