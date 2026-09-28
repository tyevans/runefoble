"""FastAPI APIRouter for Town Bulletin Board, Civic Proclamations, and Rumor Network.

Part of TASK-0263 / PRD-0024 / US-0076.
Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0002 (Domain Events via eventsource-py),
ADR-0006 (Redis Streams), and ADR-0012 (Design Tokens).
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_event_bus,
    get_settlement_repository,
    get_spicedb_client,
)
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

router = APIRouter(tags=["bulletin-board"])


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
                await bus.publish_event(STREAM_WEST_MARCHES, ev)


async def _load_settlement_for_bulletin(
    settlement_id: str,
) -> SettlementAggregate:
    repo = get_settlement_repository()
    try:
        agg = await repo.load(_to_uuid(settlement_id))
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
@router.post(
    "/settlements/{settlement_id}/bulletin",
    status_code=status.HTTP_201_CREATED,
    response_model=BulletinNoticeResponse,
)
async def pin_bulletin_notice(
    settlement_id: str,
    req: PinBulletinNoticeRequest,
    x_user_id: str | None = Header(default=None),
) -> BulletinNoticeResponse:
    """Pin a notice, monster bounty, ordinance, or rumor to the settlement bulletin board."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    spicedb = get_spicedb_client()

    await check_bulletin_board_view_permission(spicedb, settlement_id, x_user_id)
    await check_bulletin_board_edit_permission(spicedb, settlement_id, x_user_id)

    author = x_user_id or "anonymous"
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
        author_id=x_user_id,
        campaign_id=agg.state.campaign_id or None,
    )

    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    notice = agg.state.bulletin_notices[nid]
    return _format_notice_response(notice, x_user_id)


@router.get(
    "/api/v1/settlements/{settlement_id}/bulletin",
    response_model=list[BulletinNoticeResponse],
)
@router.get(
    "/settlements/{settlement_id}/bulletin",
    response_model=list[BulletinNoticeResponse],
)
async def list_bulletin_notices(
    settlement_id: str,
    board_type: str | None = None,
    category: str | None = None,
    x_user_id: str | None = Header(default=None),
) -> list[BulletinNoticeResponse]:
    """Retrieve active notices for a settlement bulletin board, filtered by board type and category."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    spicedb = get_spicedb_client()
    await check_bulletin_board_view_permission(spicedb, settlement_id, x_user_id)

    results: list[BulletinNoticeResponse] = []
    for notice in agg.state.bulletin_notices.values():
        if notice.status != "active":
            continue
        if board_type and notice.board_type.lower() != board_type.lower():
            continue
        if category and notice.category.lower() != category.lower():
            continue
        results.append(_format_notice_response(notice, x_user_id))

    return results


@router.delete(
    "/api/v1/settlements/{settlement_id}/bulletin/{notice_id}",
)
@router.delete(
    "/settlements/{settlement_id}/bulletin/{notice_id}",
)
async def remove_bulletin_notice(
    settlement_id: str,
    notice_id: str,
    reason: str = "removed",
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Remove or fulfill a notice from the bulletin board."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    if notice_id not in agg.state.bulletin_notices:
        raise HTTPException(
            status_code=404,
            detail=f"Notice '{notice_id}' not found in settlement '{settlement_id}'",
        )

    spicedb = get_spicedb_client()
    await check_bulletin_notice_edit_permission(spicedb, notice_id, settlement_id, x_user_id)

    try:
        agg.remove_bulletin_notice(
            notice_id=notice_id,
            remover_id=x_user_id or "",
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
@router.post(
    "/settlements/{settlement_id}/bulletin/{notice_id}/decrypt",
)
async def decrypt_cipher_notice(
    settlement_id: str,
    notice_id: str,
    req: DecryptCipherNoticeRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Submit a cipher decryption solution and reveal hidden quest or meeting text."""
    agg = await _load_settlement_for_bulletin(settlement_id)
    if notice_id not in agg.state.bulletin_notices:
        raise HTTPException(
            status_code=404,
            detail=f"Notice '{notice_id}' not found in settlement '{settlement_id}'",
        )

    spicedb = get_spicedb_client()
    await check_bulletin_notice_view_permission(spicedb, notice_id, settlement_id, x_user_id)

    player = x_user_id or "anonymous"
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
