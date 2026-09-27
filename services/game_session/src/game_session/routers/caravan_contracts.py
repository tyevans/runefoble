"""FastAPI APIRouter for Frontier Mercenary Caravan Contracts and Notice Board.

Part of TASK-0129 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 1 (SpiceDB Zanzibar) and Hard Invariant 2 (eventsource-py).
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Query
from game_session.caravan import CaravanContractAggregate
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_caravan_contract_repository,
    get_caravan_ledger_repository,
    get_event_bus,
    get_spicedb_client,
    get_world_contracts_index,
)
from game_session.west_marches_models import (
    AcceptCaravanContractRequest,
    DispatchContractCaravanRequest,
    FulfillContractRequest,
    PostCaravanContractRequest,
    ReportAmbushRequest,
)

router = APIRouter(prefix="/api/v1/shared-worlds", tags=["caravan-contracts"])


def _to_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _check_perm(spicedb, res_type: str, res_id: str, perm: str, user_id: str | None) -> None:
    if user_id and not await spicedb.check_permission(res_type, str(res_id), perm, "user", user_id):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks '{perm}' on {res_type}:{res_id}",
        )


async def _check_high_tier_auth(
    spicedb,
    shared_world_id: str,
    campaign_id: str,
    risk_level: str,
    user_id: str | None,
) -> None:
    """Enforce Zanzibar authorization: high-tier contracts require party leader or guild officer."""
    if risk_level.lower() in ("high", "deadly") and user_id:
        is_officer = await spicedb.check_permission(
            "shared_world", shared_world_id, "manage", "user", user_id
        )
        is_leader = await spicedb.check_permission(
            "campaign", campaign_id, "run_session", "user", user_id
        )
        if not (is_officer or is_leader):
            raise HTTPException(
                status_code=403,
                detail="High-tier mercenary contracts require guild officer or party leader authorization",
            )


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

    # Register in world notice board index
    get_world_contracts_index().setdefault(str(wid), []).append(cid)

    # Zanzibar relationship setup
    await spicedb.write_relationship(
        "caravan_contract", cid, "shared_world", "shared_world", str(wid)
    )
    if x_user_id:
        await spicedb.write_relationship("caravan_contract", cid, "poster", "user", x_user_id)

    # Publish events to Redis Stream
    bus = get_event_bus()
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

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
            if status and c_state.status != status:
                continue
            if risk_level and c_state.route_risk_level.lower() != risk_level.lower():
                continue
            if destination and c_state.destination_outpost.lower() != destination.lower():
                continue
            if min_reward is not None and c_state.reward_gold < min_reward:
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
    wid = _to_uuid(shared_world_id)
    cid = _to_uuid(contract_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, "caravan_contract", str(cid), "view", x_user_id)

    contract_repo = get_caravan_contract_repository()
    try:
        contract = await contract_repo.load(cid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Contract not found") from e

    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/accept")
async def accept_caravan_contract(
    shared_world_id: str,
    contract_id: str,
    req: AcceptCaravanContractRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Claim and accept an open contract on behalf of an adventuring party."""
    wid = _to_uuid(shared_world_id)
    cid = _to_uuid(contract_id)
    spicedb = get_spicedb_client()

    contract_repo = get_caravan_contract_repository()
    try:
        contract = await contract_repo.load(cid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Contract not found") from e

    await _check_perm(spicedb, "caravan_contract", str(cid), "claim", x_user_id)
    await _check_high_tier_auth(
        spicedb, str(wid), req.contractor_campaign_id, contract.state.route_risk_level, x_user_id
    )

    try:
        contract.accept_contract(
            contractor_campaign_id=req.contractor_campaign_id,
            contractor_party_name=req.contractor_party_name,
            accepted_by_user_id=x_user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    events = list(contract.uncommitted_events)
    await contract_repo.save(contract)

    # Sync ledger state
    ledger_repo = get_caravan_ledger_repository()
    from game_session.caravan_ledger import CaravanLedgerAggregate

    try:
        ledger = await ledger_repo.load(wid)
    except Exception:
        ledger = CaravanLedgerAggregate(wid)

    if str(cid) in ledger.state.contracts:
        ledger.state.contracts[str(cid)]["status"] = "accepted"
        ledger.state.contracts[str(cid)]["contractor_campaign_id"] = req.contractor_campaign_id
        ledger.state.contracts[str(cid)]["contractor_party_name"] = req.contractor_party_name
    await ledger_repo.save(ledger)

    if x_user_id:
        await spicedb.write_relationship(
            "caravan_contract", str(cid), "contractor", "user", x_user_id
        )

    bus = get_event_bus()
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/dispatch")
async def dispatch_contract_caravan(
    shared_world_id: str,
    contract_id: str,
    req: DispatchContractCaravanRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Dispatch caravan into frontier transit stages."""
    wid = _to_uuid(shared_world_id)
    cid = _to_uuid(contract_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, "caravan_contract", str(cid), "claim", x_user_id)

    contract_repo = get_caravan_contract_repository()
    try:
        contract = await contract_repo.load(cid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Contract not found") from e

    try:
        caravan_id = contract.dispatch_caravan(
            caravan_id=req.caravan_id,
            dispatched_by_campaign_id=req.dispatched_by_campaign_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    events = list(contract.uncommitted_events)
    await contract_repo.save(contract)

    ledger_repo = get_caravan_ledger_repository()
    from game_session.caravan_ledger import CaravanLedgerAggregate

    try:
        ledger = await ledger_repo.load(wid)
    except Exception:
        ledger = CaravanLedgerAggregate(wid)

    if str(cid) in ledger.state.contracts:
        ledger.state.contracts[str(cid)]["status"] = "in_transit"
        ledger.state.contracts[str(cid)]["caravan_id"] = caravan_id
    await ledger_repo.save(ledger)

    bus = get_event_bus()
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

    return {
        "shared_world_id": str(wid),
        "contract_id": str(cid),
        "caravan_id": caravan_id,
        "status": "in_transit",
    }


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/ambush")
async def report_contract_ambush(
    shared_world_id: str,
    contract_id: str,
    req: ReportAmbushRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Report ambush outcome during transit, updating damage and hazard history."""
    wid = _to_uuid(shared_world_id)
    cid = _to_uuid(contract_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, "caravan_contract", str(cid), "claim", x_user_id)

    contract_repo = get_caravan_contract_repository()
    try:
        contract = await contract_repo.load(cid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Contract not found") from e

    try:
        contract.report_ambush_outcome(
            stage_index=req.stage_index,
            ambush_type=req.ambush_type,
            danger_level=req.danger_level,
            outcome=req.outcome,
            cargo_loss_percentage=req.cargo_loss_percentage,
            reported_by_campaign_id=req.reported_by_campaign_id,
            notes=req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    events = list(contract.uncommitted_events)
    await contract_repo.save(contract)

    ledger_repo = get_caravan_ledger_repository()
    from game_session.caravan_ledger import CaravanLedgerAggregate

    try:
        ledger = await ledger_repo.load(wid)
    except Exception:
        ledger = CaravanLedgerAggregate(wid)

    if str(cid) in ledger.state.contracts and req.outcome == "caravan_destroyed":
        ledger.state.contracts[str(cid)]["status"] = "failed"
    await ledger_repo.save(ledger)

    bus = get_event_bus()
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

    return {
        "shared_world_id": str(wid),
        "contract_id": str(cid),
        "ambush": contract.state.ambush_history[-1],
        "status": contract.state.status,
    }


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/fulfill")
async def fulfill_caravan_contract(
    shared_world_id: str,
    contract_id: str,
    req: FulfillContractRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Deliver surviving cargo to outpost settlement, unlocking stock and paying rewards."""
    wid = _to_uuid(shared_world_id)
    cid = _to_uuid(contract_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, "caravan_contract", str(cid), "fulfill", x_user_id)

    contract_repo = get_caravan_contract_repository()
    try:
        contract = await contract_repo.load(cid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Contract not found") from e

    try:
        payout = contract.fulfill_contract()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    events = list(contract.uncommitted_events)
    await contract_repo.save(contract)

    # Dynamic settlement economy & merchant stock sync via CaravanLedgerAggregate
    ledger_repo = get_caravan_ledger_repository()
    from game_session.caravan_ledger import CaravanLedgerAggregate

    try:
        ledger = await ledger_repo.load(wid)
    except Exception:
        ledger = CaravanLedgerAggregate(wid)

    ledger.complete_contract_delivery(
        caravan_id=contract.state.caravan_id or str(cid),
        origin_outpost=contract.state.origin_outpost,
        destination_outpost=contract.state.destination_outpost,
        cargo_delivered=payout["cargo_delivered"],
    )
    ledger_events = list(ledger.uncommitted_events)
    await ledger_repo.save(ledger)

    bus = get_event_bus()
    if bus:
        for ev in events + ledger_events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

    dest = contract.state.destination_outpost.lower()
    stock = ledger.state.outpost_stocks.get(dest, {})

    return {
        "shared_world_id": str(wid),
        "contract_id": str(cid),
        "contract": contract.state.model_dump(),
        "payout": payout,
        "destination_outpost_stock": stock,
    }


__all__ = ["router"]
