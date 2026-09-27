"""Authorization and validation helpers for caravan contracts.

Part of TASK-0147 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 1 (SpiceDB Zanzibar).
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from game_session.caravan import CaravanContractAggregate
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_caravan_contract_repository,
    get_event_bus,
    get_spicedb_client,
)


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _check_perm(spicedb, res_type: str, res_id: str, perm: str, user_id: str | None) -> None:
    if user_id and not await spicedb.check_permission(res_type, str(res_id), perm, "user", user_id):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks '{perm}' on {res_type}:{res_id}",
        )


async def _check_high_tier_auth(
    spicedb, shared_world_id: str, campaign_id: str, risk_level: str, user_id: str | None
) -> None:
    """Enforce Zanzibar authorization: high-tier contracts require party leader or guild officer."""
    if risk_level.lower() in ("high", "deadly") and user_id:
        chk = spicedb.check_permission
        if not (
            await chk("shared_world", shared_world_id, "manage", "user", user_id)
            or await chk("campaign", campaign_id, "run_session", "user", user_id)
        ):
            raise HTTPException(
                status_code=403,
                detail="High-tier mercenary contracts require guild officer or party leader authorization",
            )


async def _set_contractor(spicedb, cid: UUID, user_id: str | None) -> None:
    if user_id:
        await spicedb.write_relationship(
            "caravan_contract", str(cid), "contractor", "user", user_id
        )


async def _load_contract(cid: UUID, perm: str, user_id: str | None) -> CaravanContractAggregate:
    await _check_perm(get_spicedb_client(), "caravan_contract", str(cid), perm, user_id)
    try:
        return await get_caravan_contract_repository().load(cid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Contract not found") from e


def _val_err(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def _publish(events: list[Any]) -> None:
    if bus := get_event_bus():
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)


__all__ = [
    "_check_high_tier_auth",
    "_check_perm",
    "_load_contract",
    "_publish",
    "_set_contractor",
    "_to_uuid",
    "_val_err",
]
