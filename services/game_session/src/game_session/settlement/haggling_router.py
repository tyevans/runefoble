"""FastAPI APIRouter for interactive merchant haggling and DM arbitration engine.

Part of TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0002 (Domain Events), ADR-0006 (Redis Streams).
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_TAVERN,
    STREAM_WEST_MARCHES,
    get_establishment_negotiations_index,
    get_establishment_repository,
    get_establishment_workers_index,
    get_event_bus,
    get_negotiation_repository,
    get_spicedb_client,
    get_worker_repository,
)
from game_session.settlement.auth import (
    check_establishment_read_permission,
    check_negotiation_arbitrate_permission,
    check_negotiation_participate_permission,
    check_negotiation_read_permission,
    write_negotiation_relationships,
)
from game_session.settlement.haggling import NegotiationAggregate
from game_session.settlement.haggling_models import (
    DMOverrideRequest,
    ExecuteGambitRequest,
    NegotiationSessionState,
    StartNegotiationRequest,
)

router = APIRouter(tags=["merchant-haggling"])


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _save_and_publish(repo: Any, bus: Any, agg: Any) -> None:
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_TAVERN, ev)
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)


async def _load_negotiation(nid: str) -> NegotiationAggregate:
    repo = get_negotiation_repository()
    try:
        agg = await repo.load(_to_uuid(nid))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Negotiation '{nid}' not found") from e
    if not agg.state.negotiation_id:
        raise HTTPException(status_code=404, detail=f"Negotiation '{nid}' not found")
    return agg


@router.post(
    "/api/v1/establishments/{establishment_id}/haggle", response_model=NegotiationSessionState
)
@router.post("/establishments/{establishment_id}/haggle", response_model=NegotiationSessionState)
async def haggle_establishment(
    establishment_id: str,
    req: StartNegotiationRequest,
    x_user_id: str | None = Header(default=None),
) -> NegotiationSessionState:
    """Start or advance an interactive bartering encounter within an establishment storefront."""
    spicedb = get_spicedb_client()
    await check_establishment_read_permission(spicedb, establishment_id, x_user_id)

    # 1. Determine merchant identity and item base price from establishment worker if available
    est_repo = get_establishment_repository()
    try:
        est_agg = await est_repo.load(_to_uuid(establishment_id))
        campaign_id = est_agg.state.campaign_id or req.campaign_id
    except Exception:
        campaign_id = req.campaign_id

    merchant_name = req.merchant_name or "Merchant"
    temperament = req.temperament or "Stubborn"
    merchant_id = req.merchant_id or f"merchant-{establishment_id}"
    base_price = req.base_price or 100

    worker_ids = get_establishment_workers_index().get(establishment_id, [])
    if worker_ids:
        worker_repo = get_worker_repository()
        with contextlib.suppress(Exception):
            w_agg = await worker_repo.load(_to_uuid(worker_ids[0]))
            merchant_name = w_agg.state.name or merchant_name
            temperament = w_agg.state.temperament or temperament
            merchant_id = w_agg.state.npc_id or merchant_id
            for inv_item in w_agg.state.shelf_inventory + w_agg.state.backroom_inventory:
                if inv_item.get("item_id") == req.item_id:
                    base_price = inv_item.get("price_gp", base_price)
                    break

    # 2. Instantiate and start NegotiationAggregate
    nid = uuid4()
    neg_agg = NegotiationAggregate(nid)
    neg_agg.start_negotiation(
        character_id=req.character_id,
        item_id=req.item_id,
        item_name=req.item_name or req.item_id,
        original_price=base_price,
        initial_offer_gp=req.initial_offer_gp or req.offered_price,
        establishment_id=establishment_id,
        merchant_id=merchant_id,
        merchant_name=merchant_name,
        campaign_id=campaign_id,
        session_id=req.session_id,
        temperament=temperament,
    )

    # 3. If an initial gambit was selected, execute it immediately
    if req.gambit:
        neg_agg.execute_gambit(
            character_id=req.character_id,
            gambit=req.gambit,
            roll_value=req.roll_value,
            charisma_mod=req.charisma_modifier,
            offered_price=req.initial_offer_gp or req.offered_price,
        )

    repo = get_negotiation_repository()
    bus = get_event_bus()
    await _save_and_publish(repo, bus, neg_agg)

    # 4. Write SpiceDB Zanzibar tuples
    await write_negotiation_relationships(
        spicedb,
        negotiation_id=str(nid),
        establishment_id=establishment_id,
        campaign_id=campaign_id,
        session_id=req.session_id,
        participant_id=x_user_id,
    )

    get_establishment_negotiations_index().setdefault(establishment_id, []).append(str(nid))
    return neg_agg.state


@router.post("/api/v1/haggling/start", response_model=NegotiationSessionState)
@router.post("/haggling/start", response_model=NegotiationSessionState)
async def start_haggling_session(
    req: StartNegotiationRequest,
    x_user_id: str | None = Header(default=None),
) -> NegotiationSessionState:
    """Explicitly start an isolated negotiation session."""
    nid = uuid4()
    neg_agg = NegotiationAggregate(nid)
    neg_agg.start_negotiation(
        character_id=req.character_id,
        item_id=req.item_id,
        item_name=req.item_name or req.item_id,
        original_price=req.base_price or 100,
        initial_offer_gp=req.initial_offer_gp or req.offered_price,
        merchant_id=req.merchant_id or f"npc-merchant-{nid.hex[:6]}",
        merchant_name=req.merchant_name or "Merchant",
        campaign_id=req.campaign_id,
        session_id=req.session_id,
        temperament=req.temperament or "Stubborn",
    )

    repo = get_negotiation_repository()
    bus = get_event_bus()
    await _save_and_publish(repo, bus, neg_agg)

    spicedb = get_spicedb_client()
    await write_negotiation_relationships(
        spicedb,
        negotiation_id=str(nid),
        campaign_id=req.campaign_id,
        session_id=req.session_id,
        participant_id=x_user_id,
    )

    return neg_agg.state


@router.post("/api/v1/haggling/{negotiation_id}/gambit", response_model=NegotiationSessionState)
@router.post("/haggling/{negotiation_id}/gambit", response_model=NegotiationSessionState)
async def execute_gambit_route(
    negotiation_id: str,
    req: ExecuteGambitRequest,
    x_user_id: str | None = Header(default=None),
) -> NegotiationSessionState:
    """Submit a persuasive gambit (Flattery, Bulk Order, Point Out Flaw, Intimidation, Walk Away)."""
    spicedb = get_spicedb_client()
    await check_negotiation_participate_permission(spicedb, negotiation_id, x_user_id)

    neg_agg = await _load_negotiation(negotiation_id)
    try:
        neg_agg.execute_gambit(
            character_id=req.character_id,
            gambit=req.gambit,
            roll_value=req.roll_value,
            charisma_mod=req.charisma_modifier,
            offered_price=req.offered_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    repo = get_negotiation_repository()
    bus = get_event_bus()
    await _save_and_publish(repo, bus, neg_agg)
    return neg_agg.state


@router.patch(
    "/api/v1/haggling/{negotiation_id}/dm-override", response_model=NegotiationSessionState
)
@router.patch("/haggling/{negotiation_id}/dm-override", response_model=NegotiationSessionState)
async def dm_negotiation_override(
    negotiation_id: str,
    req: DMOverrideRequest,
    x_user_id: str | None = Header(default=None),
    x_runefoble_role: str | None = Header(default=None, alias="X-RuneFoble-Role"),
) -> NegotiationSessionState:
    """Game Master arbitration control: nudge mood, inject dialogue barks, or override price."""
    spicedb = get_spicedb_client()
    # Check SpiceDB Zanzibar permission unless authorized DM role header is set for dev/test
    if x_runefoble_role not in ("dungeon_master", "game_master", "dm"):
        await check_negotiation_arbitrate_permission(spicedb, negotiation_id, x_user_id)

    neg_agg = await _load_negotiation(negotiation_id)
    try:
        neg_agg.dm_override(
            dm_user_id=x_user_id or "dm_operator",
            action=req.action,
            override_price_gp=req.override_price_gp or req.override_price,
            narrative_bark=req.narrative_bark,
            patience_delta=req.patience_delta,
            mood_delta=req.mood_delta,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    repo = get_negotiation_repository()
    bus = get_event_bus()
    await _save_and_publish(repo, bus, neg_agg)
    return neg_agg.state


@router.get("/api/v1/haggling/{negotiation_id}", response_model=NegotiationSessionState)
@router.get("/haggling/{negotiation_id}", response_model=NegotiationSessionState)
async def get_negotiation_state(
    negotiation_id: str,
    x_user_id: str | None = Header(default=None),
) -> NegotiationSessionState:
    """Retrieve the live state and dialogue history of an interactive bartering encounter."""
    spicedb = get_spicedb_client()
    await check_negotiation_read_permission(spicedb, negotiation_id, x_user_id)
    neg_agg = await _load_negotiation(negotiation_id)
    return neg_agg.state


@router.post("/api/v1/haggling/{negotiation_id}/accept", response_model=NegotiationSessionState)
@router.post("/haggling/{negotiation_id}/accept", response_model=NegotiationSessionState)
async def accept_negotiation(
    negotiation_id: str,
    x_user_id: str | None = Header(default=None),
) -> NegotiationSessionState:
    """Accept the merchant's current counter-offer and finalize the deal."""
    spicedb = get_spicedb_client()
    await check_negotiation_participate_permission(spicedb, negotiation_id, x_user_id)
    neg_agg = await _load_negotiation(negotiation_id)
    try:
        neg_agg.dm_override(
            dm_user_id=x_user_id or "player",
            action="accept_deal",
            override_price_gp=neg_agg.state.counter_price,
            narrative_bark="Deal accepted by customer.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    repo = get_negotiation_repository()
    bus = get_event_bus()
    await _save_and_publish(repo, bus, neg_agg)
    return neg_agg.state
