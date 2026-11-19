"""FastAPI APIRouter for West Marches caravan logistics and regional merchant stock.

Part of TASK-0127 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 1 (SpiceDB Zanzibar) and Hard Invariant 2 (eventsource-py).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from game_session.caravan.ledger import CaravanLedgerAggregate
from game_session.dependencies import get_caravan_ledger_repository, get_event_bus
from game_session.events import STREAM_WEST_MARCHES
from game_session.settlement.auth.tokens import CallerId, get_principal
from game_session.west_marches_models import (
    CompleteCaravanRequest,
    DispatchCaravanRequest,
)
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import require_subject
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(
    dependencies=[Depends(get_principal)],
    prefix="/api/v1/shared-worlds",
    tags=["caravan-trade"],
)


async def _load_ledger(wid: UUID) -> tuple[Any, CaravanLedgerAggregate]:
    """Load the world's caravan ledger, or start an empty one when none exists yet."""
    repo = get_caravan_ledger_repository()
    return repo, await load_or_create(repo, wid, CaravanLedgerAggregate)


@router.post("/{shared_world_id}/caravans/dispatch", status_code=201)
async def dispatch_caravan(
    caller_id: CallerId,
    shared_world_id: str,
    req: DispatchCaravanRequest,
) -> dict[str, Any]:
    """Dispatch scheduled caravan delivering crafted goods/reagents between outposts."""
    wid = parse_uuid(shared_world_id, field="shared_world_id")
    spicedb = get_spicedb_client()
    await require_subject(spicedb, "shared_world", str(wid), "trade", caller_id)

    repo, ledger = await _load_ledger(wid)

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
            await publish_or_fail(bus, STREAM_WEST_MARCHES, ev)

    return {"shared_world_id": str(wid), "caravan": ledger.state.caravans[cid]}


@router.post("/{shared_world_id}/caravans/{caravan_id}/complete")
async def complete_caravan_trade(
    caller_id: CallerId,
    shared_world_id: str,
    caravan_id: str,
    req: CompleteCaravanRequest,
) -> dict[str, Any]:
    """Complete caravan transit, delivering cargo and unlocking regional merchant stock."""
    wid = parse_uuid(shared_world_id, field="shared_world_id")
    spicedb = get_spicedb_client()
    await require_subject(spicedb, "shared_world", str(wid), "trade", caller_id)

    repo, ledger = await _load_ledger(wid)

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
            await publish_or_fail(bus, STREAM_WEST_MARCHES, ev)

    dest = caravan["destination_outpost"].lower()
    stock = ledger.state.outpost_stocks.get(dest, {})
    return {
        "shared_world_id": str(wid),
        "caravan": caravan,
        "destination_outpost_stock": stock,
    }


@router.get("/{shared_world_id}/outposts/{outpost_name}/merchant-stock")
async def get_outpost_merchant_stock(
    caller_id: CallerId,
    shared_world_id: str,
    outpost_name: str,
) -> dict[str, Any]:
    """Retrieve merchant stock and rare crafting reagents unlocked at a regional outpost."""
    wid = parse_uuid(shared_world_id, field="shared_world_id")
    spicedb = get_spicedb_client()
    await require_subject(spicedb, "shared_world", str(wid), "view", caller_id)

    _, ledger = await _load_ledger(wid)

    dest = outpost_name.lower()
    stock = ledger.state.outpost_stocks.get(dest, {"inventory": {}, "workshop_reagents": {}})
    return {
        "shared_world_id": str(wid),
        "outpost_name": outpost_name,
        "stock": stock,
    }
