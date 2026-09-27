"""Caravan lifecycle router: accept, dispatch, ambush, and settlement fulfillment."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header
from game_session.caravan import CaravanContractAggregate
from game_session.caravan_ledger import CaravanLedgerAggregate
from game_session.dependencies import (
    get_caravan_contract_repository,
    get_caravan_ledger_repository,
    get_spicedb_client,
)
from game_session.routers.caravan_contracts.auth import (
    _check_high_tier_auth,
    _load_contract,
    _publish,
    _set_contractor,
    _to_uuid,
    _val_err,
)
from game_session.west_marches_models import (
    AcceptCaravanContractRequest,
    DispatchContractCaravanRequest,
    FulfillContractRequest,
    ReportAmbushRequest,
)

router = APIRouter(prefix="/api/v1/shared-worlds", tags=["caravan-contracts"])


async def _init(
    wid_s: str, cid_s: str, perm: str, uid: str | None
) -> tuple[UUID, UUID, CaravanContractAggregate]:
    wid, cid = _to_uuid(wid_s), _to_uuid(cid_s)
    return wid, cid, await _load_contract(cid, perm, uid)


async def _ledger(wid: UUID) -> tuple[Any, CaravanLedgerAggregate]:
    repo = get_caravan_ledger_repository()
    try:
        return repo, await repo.load(wid)
    except Exception:
        return repo, CaravanLedgerAggregate(wid)


async def _sync(
    contract: CaravanContractAggregate,
    wid: UUID,
    cid: UUID,
    updates: dict[str, Any] | None = None,
    extra: list[Any] = (),
) -> None:
    events = list(contract.uncommitted_events) + list(extra)
    await get_caravan_contract_repository().save(contract)
    await _publish(events)
    if updates:
        repo, ledger = await _ledger(wid)
        if str(cid) in ledger.state.contracts:
            ledger.state.contracts[str(cid)].update(updates)
            await repo.save(ledger)


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/accept")
async def accept_caravan_contract(
    shared_world_id: str,
    contract_id: str,
    req: AcceptCaravanContractRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Claim and accept an open contract on behalf of an adventuring party."""
    wid, cid, contract = await _init(shared_world_id, contract_id, "claim", x_user_id)
    spicedb = get_spicedb_client()
    await _check_high_tier_auth(
        spicedb, str(wid), req.contractor_campaign_id, contract.state.route_risk_level, x_user_id
    )
    _val_err(
        contract.accept_contract,
        contractor_campaign_id=req.contractor_campaign_id,
        contractor_party_name=req.contractor_party_name,
        accepted_by_user_id=x_user_id,
    )
    updates = {
        "status": "accepted",
        "contractor_campaign_id": req.contractor_campaign_id,
        "contractor_party_name": req.contractor_party_name,
    }
    await _sync(contract, wid, cid, updates)
    await _set_contractor(spicedb, cid, x_user_id)
    return {"shared_world_id": str(wid), "contract": contract.state.model_dump()}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/dispatch")
async def dispatch_contract_caravan(
    shared_world_id: str,
    contract_id: str,
    req: DispatchContractCaravanRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Dispatch caravan into frontier transit stages."""
    wid, cid, contract = await _init(shared_world_id, contract_id, "claim", x_user_id)
    cid_out = _val_err(
        contract.dispatch_caravan,
        caravan_id=req.caravan_id,
        dispatched_by_campaign_id=req.dispatched_by_campaign_id,
    )
    await _sync(contract, wid, cid, {"status": "in_transit", "caravan_id": cid_out})
    res = {"shared_world_id": str(wid), "contract_id": str(cid), "caravan_id": cid_out}
    return {**res, "status": "in_transit"}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/ambush")
async def report_contract_ambush(
    shared_world_id: str,
    contract_id: str,
    req: ReportAmbushRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Report ambush outcome during transit, updating damage and hazard history."""
    wid, cid, contract = await _init(shared_world_id, contract_id, "claim", x_user_id)
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
    await _sync(contract, wid, cid, fail)
    res = {"shared_world_id": str(wid), "contract_id": str(cid)}
    return {**res, "ambush": contract.state.ambush_history[-1], "status": contract.state.status}


@router.post("/{shared_world_id}/caravans/contracts/{contract_id}/fulfill")
async def fulfill_caravan_contract(
    shared_world_id: str,
    contract_id: str,
    req: FulfillContractRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Deliver surviving cargo to outpost settlement, unlocking stock and paying rewards."""
    wid, cid, contract = await _init(shared_world_id, contract_id, "fulfill", x_user_id)
    payout = _val_err(contract.fulfill_contract)

    repo, ledger = await _ledger(wid)
    st = contract.state
    ledger.complete_contract_delivery(
        caravan_id=st.caravan_id or str(cid),
        origin_outpost=st.origin_outpost,
        destination_outpost=st.destination_outpost,
        cargo_delivered=payout["cargo_delivered"],
    )
    ledger_events = list(ledger.uncommitted_events)
    await repo.save(ledger)
    await _sync(contract, wid, cid, extra=ledger_events)

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
