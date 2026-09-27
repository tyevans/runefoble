"""Caravan notice board router: post, list, and view contracts.

Part of TASK-0147 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Query
from game_session.caravan import CaravanContractAggregate
from game_session.dependencies import (
    get_caravan_contract_repository,
    get_spicedb_client,
    get_world_contracts_index,
)
from game_session.routers.caravan_contracts.auth import (
    _check_high_tier_auth,
    _check_perm,
    _publish,
    _to_uuid,
)
from game_session.west_marches_models import PostCaravanContractRequest

router = APIRouter(prefix="/api/v1/shared-worlds", tags=["caravan-contracts"])


@router.post("/{shared_world_id}/caravans/contracts", status_code=201)
async def post_caravan_contract(
    shared_world_id: str,
    req: PostCaravanContractRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Post an asynchronous mercenary escort contract to the shared world notice board."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, "shared_world", str(wid), "trade", x_user_id)
    await _check_high_tier_auth(
        spicedb, str(wid), req.posted_by_campaign_id, req.route_risk_level, x_user_id
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
        poster_user_id=x_user_id,
        expires_in_turns=req.expires_in_turns,
    )
    events = list(contract.uncommitted_events)
    await contract_repo.save(contract)

    # Register in world notice board index and write Zanzibar relations
    get_world_contracts_index().setdefault(str(wid), []).append(cid)
    await spicedb.write_relationship(
        "caravan_contract", cid, "shared_world", "shared_world", str(wid)
    )
    if x_user_id:
        await spicedb.write_relationship("caravan_contract", cid, "poster", "user", x_user_id)

    await _publish(events)
    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


@router.get("/{shared_world_id}/caravans/contracts")
async def list_caravan_contracts(
    shared_world_id: str,
    status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    destination: str | None = Query(default=None),
    min_reward: int | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Query available notice board contracts applying optional frontier filters."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, "shared_world", str(wid), "view", x_user_id)

    contract_repo = get_caravan_contract_repository()
    cids = get_world_contracts_index().get(str(wid), [])
    contracts: list[dict[str, Any]] = []

    for c_id in cids:
        try:
            c_agg = await contract_repo.load(UUID(c_id))
            c_state = c_agg.state
            if (
                (status and c_state.status != status)
                or (risk_level and c_state.route_risk_level.lower() != risk_level.lower())
                or (destination and c_state.destination_outpost.lower() != destination.lower())
                or (min_reward is not None and c_state.reward_gold < min_reward)
            ):
                continue
            contracts.append(c_state.model_dump())
        except Exception:
            continue

    return {"shared_world_id": str(wid), "contracts": contracts}


@router.get("/{shared_world_id}/caravans/contracts/{contract_id}")
async def get_caravan_contract(
    shared_world_id: str,
    contract_id: str,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Retrieve details and manifest for a specific caravan escort contract."""
    wid, cid = _to_uuid(shared_world_id), _to_uuid(contract_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, "caravan_contract", str(cid), "view", x_user_id)

    try:
        contract = await get_caravan_contract_repository().load(cid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Contract not found") from e

    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


__all__ = ["get_caravan_contract", "list_caravan_contracts", "post_caravan_contract", "router"]
