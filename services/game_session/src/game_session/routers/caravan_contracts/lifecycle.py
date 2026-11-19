"""Caravan lifecycle router: accept, dispatch, ambush, and settlement fulfillment."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from game_session.caravan import CaravanContractAggregate
from game_session.caravan.ledger import CaravanLedgerAggregate
from game_session.routers.caravan_contracts.auth import (
    _check_high_tier_auth,
    _load_contract,
    _set_contractor,
    _val_err,
)
from game_session.shared.container_access import EventBus
from game_session.shared.identity import CallerId, get_principal
from game_session.shared.streams import STREAM_WEST_MARCHES
from game_session.west_marches_models import (
    AcceptCaravanContractRequest,
    DispatchContractCaravanRequest,
    FulfillContractRequest,
    ReportAmbushRequest,
)
from game_session.world.repositories import WorldRepos, WorldRepositories
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(
    dependencies=[Depends(get_principal)],
    prefix="/api/v1/shared-worlds",
    tags=["caravan-contracts"],
)


async def _init(
    repos: WorldRepositories, wid_s: str, cid_s: str, perm: str, uid: str
) -> tuple[UUID, UUID, CaravanContractAggregate]:
    wid, cid = parse_uuid(wid_s, field="wid_s"), parse_uuid(cid_s, field="cid_s")
    return wid, cid, await _load_contract(repos.caravan_contracts, cid, perm, uid)


async def _ledger(repos: WorldRepositories, wid: UUID) -> tuple[Any, CaravanLedgerAggregate]:
    repo = repos.caravan_ledgers
    return repo, await load_or_create(repo, wid, CaravanLedgerAggregate)


async def _sync(
    repos: WorldRepositories,
    bus_provider: EventBusProvider,
    contract: CaravanContractAggregate,
    wid: UUID,
    cid: UUID,
    updates: dict[str, Any] | None = None,
    extra: list[Any] = (),
) -> None:
    events = list(contract.uncommitted_events) + list(extra)
    await repos.caravan_contracts.save(contract)
    if bus := bus_provider.get():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    if updates:
        repo, ledger = await _ledger(repos, wid)
        if str(cid) in ledger.state.contracts:
            ledger.state.contracts[str(cid)].update(updates)
            await repo.save(ledger)


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/accept")
async def accept_caravan_contract(
    caller_id: CallerId,
    shared_world_id: str,
    contract_id: str,
    req: AcceptCaravanContractRequest,
    repos: WorldRepos,
    events: EventBus,
) -> dict[str, Any]:
    """Claim and accept an open contract on behalf of an adventuring party."""
    wid, cid, contract = await _init(repos, shared_world_id, contract_id, "claim", caller_id)
    spicedb = get_spicedb_client()
    await _check_high_tier_auth(
        spicedb, str(wid), req.contractor_campaign_id, contract.state.route_risk_level, caller_id
    )
    _val_err(
        contract.accept_contract,
        contractor_campaign_id=req.contractor_campaign_id,
        contractor_party_name=req.contractor_party_name,
        accepted_by_user_id=caller_id,
    )
    updates = {
        "status": "accepted",
        "contractor_campaign_id": req.contractor_campaign_id,
        "contractor_party_name": req.contractor_party_name,
    }
    await _sync(repos, events, contract, wid, cid, updates)
    await _set_contractor(spicedb, cid, caller_id)
    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/dispatch")
async def dispatch_contract_caravan(
    caller_id: CallerId,
    shared_world_id: str,
    contract_id: str,
    req: DispatchContractCaravanRequest,
    repos: WorldRepos,
    events: EventBus,
) -> dict[str, Any]:
    """Dispatch caravan into frontier transit stages."""
    wid, cid, contract = await _init(repos, shared_world_id, contract_id, "claim", caller_id)
    cid_out = _val_err(
        contract.dispatch_caravan,
        caravan_id=req.caravan_id,
        dispatched_by_campaign_id=req.dispatched_by_campaign_id,
    )
    await _sync(repos, events, contract, wid, cid, {"status": "in_transit", "caravan_id": cid_out})
    res = {"shared_world_id": str(wid), "contract_id": str(cid), "caravan_id": cid_out}
    return {**res, "status": "in_transit"}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/ambush")
async def report_contract_ambush(
    caller_id: CallerId,
    shared_world_id: str,
    contract_id: str,
    req: ReportAmbushRequest,
    repos: WorldRepos,
    events: EventBus,
) -> dict[str, Any]:
    """Report ambush outcome during transit, updating damage and hazard history."""
    wid, cid, contract = await _init(repos, shared_world_id, contract_id, "claim", caller_id)
    _val_err(
        contract.report_ambush_outcome,
        stage_index=req.stage_index,
        ambush_type=req.ambush_type,
        danger_level=req.danger_level,
        outcome=req.outcome,
        cargo_loss_percentage=req.cargo_loss_percentage,
        reported_by_campaign_id=req.reported_by_campaign_id,
        notes=req.notes,
    )
    fail = {"status": "failed"} if req.outcome == "caravan_destroyed" else None
    await _sync(repos, events, contract, wid, cid, fail)
    res = {"shared_world_id": str(wid), "contract_id": str(cid)}
    return {**res, "ambush": contract.state.ambush_history[-1], "status": contract.state.status}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/fulfill")
async def fulfill_caravan_contract(
    caller_id: CallerId,
    shared_world_id: str,
    contract_id: str,
    req: FulfillContractRequest,
    repos: WorldRepos,
    events: EventBus,
) -> dict[str, Any]:
    """Deliver surviving cargo to outpost settlement, unlocking stock and paying rewards."""
    wid, cid, contract = await _init(repos, shared_world_id, contract_id, "fulfill", caller_id)
    payout = _val_err(contract.fulfill_contract)

    repo, ledger = await _ledger(repos, wid)
    st = contract.state
    ledger.complete_contract_delivery(
        caravan_id=st.caravan_id or str(cid),
        origin_outpost=st.origin_outpost,
        destination_outpost=st.destination_outpost,
        cargo_delivered=payout["cargo_delivered"],
    )
    ledger_events = list(ledger.uncommitted_events)
    await repo.save(ledger)
    await _sync(repos, events, contract, wid, cid, extra=ledger_events)

    dest = st.destination_outpost.lower()
    return {
        "shared_world_id": str(wid),
        "contract_id": str(cid),
        "contract": st.model_dump(),
        "payout": payout,
        "destination_outpost_stock": ledger.state.outpost_stocks.get(dest, {}),
    }


__all__ = [
    "accept_caravan_contract",
    "dispatch_contract_caravan",
    "fulfill_caravan_contract",
    "report_contract_ambush",
    "router",
]
