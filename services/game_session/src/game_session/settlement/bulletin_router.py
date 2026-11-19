"""FastAPI APIRouter for Town Bulletin Board, Civic Proclamations, and Rumor Network.

Part of TASK-0263 / PRD-0024 / US-0076.
Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0002 (Domain Events via eventsource-py),
ADR-0006 (Redis Streams), and ADR-0012 (Design Tokens).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from game_session.dependencies import get_event_bus, get_settlement_repository
from game_session.events import STREAM_WEST_MARCHES
from game_session.settlement.auth.tokens import CallerId, get_principal
from game_session.settlement.bulletin_auth import (
    check_bulletin_board_edit_permission,
    check_bulletin_board_view_permission,
    check_bulletin_notice_edit_permission,
    check_bulletin_notice_view_permission,
    delete_bulletin_notice_relationships,
    write_bulletin_notice_relationships,
)
from game_session.settlement.models import (
    BulletinNoticeResponse,
    BulletinNoticeState,
    DecryptCipherNoticeRequest,
    PinBulletinNoticeRequest,
)
from game_session.settlement.settlement_aggregate import SettlementAggregate
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(dependencies=[Depends(get_principal)], tags=["bulletin-board"])


async def _save_and_publish(repo: Any, bus: Any, agg: Any) -> None:
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    if bus:
        for ev in events:
            await publish_or_fail(bus, STREAM_WEST_MARCHES, ev)


async def _load_settlement_for_bulletin(
    settlement_id: str,
) -> SettlementAggregate:
    repo = get_settlement_repository()
    settlement_uuid = parse_uuid(settlement_id, field="settlement_id")
    try:
        agg = await repo.load(settlement_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Settlement '{settlement_id}' not found"
        ) from e
    if not agg.state.is_founded:
        raise HTTPException(status_code=404, detail=f"Settlement '{settlement_id}' not found")
    return agg


def _format_notice_response(
    notice: BulletinNoticeState, user_id: str | None
) -> BulletinNoticeResponse:
    is_decrypted = False
    hidden_content = None
    if notice.cipher_encoded:
        if user_id and (user_id in notice.decrypted_by or user_id == notice.author_id):
            is_decrypted = True
            hidden_content = notice.hidden_content
    else:
        is_decrypted = True

    return BulletinNoticeResponse(
        notice_id=notice.notice_id,
        settlement_id=notice.settlement_id,
        board_type=notice.board_type,
        title=notice.title,
        author_id=notice.author_id,
        category=notice.category,
        content=notice.content,
        wax_sealed=notice.wax_sealed,
        cipher_encoded=notice.cipher_encoded,
        cipher_puzzle=notice.cipher_puzzle,
        cipher_hint=notice.cipher_hint,
        hidden_content=hidden_content,
        is_decrypted=is_decrypted,
        status=notice.status,
        created_at=notice.created_at,
        metadata=dict(notice.metadata),
    )


@router.post(
    "/api/v1/settlements/{settlement_id}/bulletin",
    status_code=status.HTTP_201_CREATED,
    response_model=BulletinNoticeResponse,
)
async def pin_bulletin_notice(
    caller_id: CallerId,
    settlement_id: str,
    req: PinBulletinNoticeRequest,
) -> BulletinNoticeResponse:
    """Pin a notice, monster bounty, ordinance, or rumor to the settlement bulletin board."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    spicedb = get_spicedb_client()

    await check_bulletin_board_view_permission(spicedb, settlement_id, caller_id)
    await check_bulletin_board_edit_permission(spicedb, settlement_id, caller_id)

    author = caller_id
    try:
        nid = agg.pin_bulletin_notice(
            title=req.title,
            content=req.content,
            author_id=author,
            board_type=req.board_type,
            category=req.category,
            wax_sealed=req.wax_sealed,
            cipher_encoded=req.cipher_encoded,
            cipher_puzzle=req.cipher_puzzle,
            cipher_solution=req.cipher_solution,
            cipher_hint=req.cipher_hint,
            hidden_content=req.hidden_content,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await write_bulletin_notice_relationships(
        spicedb,
        notice_id=nid,
        settlement_id=settlement_id,
        author_id=caller_id,
        campaign_id=agg.state.campaign_id or None,
    )

    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    notice = agg.state.bulletin_notices[nid]
    return _format_notice_response(notice, caller_id)


@router.get(
    "/api/v1/settlements/{settlement_id}/bulletin",
    response_model=list[BulletinNoticeResponse],
)
async def list_bulletin_notices(
    caller_id: CallerId,
    settlement_id: str,
    board_type: str | None = None,
    category: str | None = None,
) -> list[BulletinNoticeResponse]:
    """Retrieve active notices for a settlement bulletin board, filtered by board type and category."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    spicedb = get_spicedb_client()
    await check_bulletin_board_view_permission(spicedb, settlement_id, caller_id)

    results: list[BulletinNoticeResponse] = []
    for notice in agg.state.bulletin_notices.values():
        if notice.status != "active":
            continue
        if board_type and notice.board_type.lower() != board_type.lower():
            continue
        if category and notice.category.lower() != category.lower():
            continue
        results.append(_format_notice_response(notice, caller_id))

    return results


@router.delete(
    "/api/v1/settlements/{settlement_id}/bulletin/{notice_id}",
)
async def remove_bulletin_notice(
    caller_id: CallerId,
    settlement_id: str,
    notice_id: str,
    reason: str = "removed",
) -> dict[str, Any]:
    """Remove or fulfill a notice from the bulletin board."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    if notice_id not in agg.state.bulletin_notices:
        raise HTTPException(
            status_code=404,
            detail=f"Notice '{notice_id}' not found in settlement '{settlement_id}'",
        )

    spicedb = get_spicedb_client()
    await check_bulletin_notice_edit_permission(spicedb, notice_id, settlement_id, caller_id)

    try:
        agg.remove_bulletin_notice(
            notice_id=notice_id,
            remover_id=caller_id,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    notice = agg.state.bulletin_notices[notice_id]
    await delete_bulletin_notice_relationships(
        spicedb,
        notice_id=notice_id,
        settlement_id=settlement_id,
        author_id=notice.author_id,
        campaign_id=agg.state.campaign_id or None,
    )

    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    return {
        "status": "removed",
        "notice_id": notice_id,
        "settlement_id": settlement_id,
    }


@router.post(
    "/api/v1/settlements/{settlement_id}/bulletin/{notice_id}/decrypt",
)
async def decrypt_cipher_notice(
    caller_id: CallerId,
    settlement_id: str,
    notice_id: str,
    req: DecryptCipherNoticeRequest,
) -> dict[str, Any]:
    """Submit a cipher decryption solution and reveal hidden quest or meeting text."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    if notice_id not in agg.state.bulletin_notices:
        raise HTTPException(
            status_code=404,
            detail=f"Notice '{notice_id}' not found in settlement '{settlement_id}'",
        )

    spicedb = get_spicedb_client()
    await check_bulletin_notice_view_permission(spicedb, notice_id, settlement_id, caller_id)

    player = caller_id
    try:
        secret = agg.decrypt_cipher_notice(
            notice_id=notice_id,
            player_id=player,
            solution=req.solution,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    notice = agg.state.bulletin_notices[notice_id]
    return {
        "status": "decrypted",
        "notice_id": notice_id,
        "settlement_id": settlement_id,
        "player_id": player,
        "title": notice.title,
        "decrypted_content": secret,
    }
