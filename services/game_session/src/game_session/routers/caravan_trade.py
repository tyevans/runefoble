"""FastAPI APIRouter for West Marches caravan logistics and regional merchant stock.

Part of TASK-0127 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 1 (SpiceDB Zanzibar) and Hard Invariant 2 (eventsource-py).
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_caravan_ledger_repository,
    get_event_bus,
    get_spicedb_client,
)
from game_session.west_marches_models import (
    CompleteCaravanRequest,
    DispatchCaravanRequest,
)

router = APIRouter(prefix="/api/v1/shared-worlds", tags=["caravan-trade"])


def _to_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _check_perm(spicedb, res_id: str, perm: str, user_id: str | None) -> None:
    if user_id and not await spicedb.check_permission(
        "shared_world", str(res_id), perm, "user", user_id
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks '{perm}' on shared_world:{res_id}",
        )


@router.post("/{shared_world_id}/caravans/dispatch", status_code=201)
async def dispatch_caravan(
    shared_world_id: str,
    req: DispatchCaravanRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Dispatch scheduled caravan delivering crafted goods/reagents between outposts."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "trade", x_user_id)

    repo = get_caravan_ledger_repository()
    from game_session.caravan_ledger import CaravanLedgerAggregate

    try:
        ledger = await repo.load(wid)
    except Exception:
        ledger = CaravanLedgerAggregate(wid)

    cid = ledger.dispatch_caravan(
        origin_outpost=req.origin_outpost,
        destination_outpost=req.destination_outpost,
        cargo=req.cargo,
        dispatched_by_campaign_id=req.dispatched_by_campaign_id,
        transit_turns=req.transit_turns,
    )
    events_to_emit = list(ledger.uncommitted_events)
    await repo.save(ledger)

    bus = get_event_bus()
    if bus:
        for ev in events_to_emit:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

    return {"shared_world_id": str(wid), "caravan": ledger.state.caravans[cid]}


@router.post("/{shared_world_id}/caravans/{caravan_id}/complete")
async def complete_caravan_trade(
    shared_world_id: str,
    caravan_id: str,
    req: CompleteCaravanRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Complete caravan transit, delivering cargo and unlocking regional merchant stock."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "trade", x_user_id)

    repo = get_caravan_ledger_repository()
    from game_session.caravan_ledger import CaravanLedgerAggregate

    try:
        ledger = await repo.load(wid)
    except Exception:
        ledger = CaravanLedgerAggregate(wid)

    try:
        caravan = ledger.complete_caravan_trade(
            caravan_id=caravan_id,
            unlocked_stock=req.unlocked_stock,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    events_to_emit = list(ledger.uncommitted_events)
    await repo.save(ledger)

    bus = get_event_bus()
    if bus:
        for ev in events_to_emit:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

    dest = caravan["destination_outpost"].lower()
    stock = ledger.state.outpost_stocks.get(dest, {})
    return {
        "shared_world_id": str(wid),
        "caravan": caravan,
        "destination_outpost_stock": stock,
    }


@router.get("/{shared_world_id}/outposts/{outpost_name}/merchant-stock")
async def get_outpost_merchant_stock(
    shared_world_id: str,
    outpost_name: str,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Retrieve merchant stock and rare crafting reagents unlocked at a regional outpost."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "view", x_user_id)

    repo = get_caravan_ledger_repository()
    from game_session.caravan_ledger import CaravanLedgerAggregate

    try:
        ledger = await repo.load(wid)
    except Exception:
        ledger = CaravanLedgerAggregate(wid)

    dest = outpost_name.lower()
    stock = ledger.state.outpost_stocks.get(dest, {"inventory": {}, "workshop_reagents": {}})
    return {
        "shared_world_id": str(wid),
        "outpost_name": outpost_name,
        "stock": stock,
    }
