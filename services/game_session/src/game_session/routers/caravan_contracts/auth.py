"""Authorization and validation helpers for caravan contracts.

Part of TASK-0147 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 1 (SpiceDB Zanzibar).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from game_session.caravan import CaravanContractAggregate
from game_session.dependencies import get_caravan_contract_repository
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject, require_subject
from runefoble_platform.aggregate_loading import load_or_404


async def _check_high_tier_auth(
    spicedb, shared_world_id: str, campaign_id: str, risk_level: str, user_id: str
) -> None:
    """Enforce Zanzibar authorization: high-tier contracts require party leader or guild officer."""
    is_high_tier = risk_level.lower() in ("high", "deadly")
    if is_high_tier and not (
        await check_subject(spicedb, "shared_world", shared_world_id, "manage", user_id)
        or await check_subject(spicedb, "campaign", campaign_id, "run_session", user_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="High-tier mercenary contracts require guild officer or party leader authorization",
        )


async def _set_contractor(spicedb, cid: UUID, user_id: str) -> None:
    await spicedb.write_relationship("caravan_contract", str(cid), "contractor", "user", user_id)


async def _load_contract(cid: UUID, perm: str, user_id: str) -> CaravanContractAggregate:
    await require_subject(get_spicedb_client(), "caravan_contract", str(cid), perm, user_id)
    return await load_or_404(get_caravan_contract_repository(), cid, "Contract not found")


def _val_err(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


__all__ = [
    "_check_high_tier_auth",
    "_load_contract",
    "_set_contractor",
    "_val_err",
]
