"""Data loaders, UUID converters, and event persistence for worker domain.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_establishment_repository,
    get_spicedb_client,
    get_worker_repository,
)
from game_session.settlement.auth import (
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_npc_read_permission,
    check_npc_write_permission,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.worker_aggregate import NPCWorkerAggregate


def to_uuid(val: Any) -> UUID:
    """Coerce value to UUID or raise 400."""
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def save_and_publish(repo: Any, bus: Any, agg: Any) -> None:
    """Persist uncommitted aggregate events and publish to West Marches stream."""
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)


async def load_establishment(eid: str, perm: str, uid: str | None) -> EstablishmentAggregate:
    """Load establishment aggregate and enforce Zanzibar read/write permissions."""
    repo = get_establishment_repository()
    try:
        agg = await repo.load(to_uuid(eid))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found") from e
    if not agg.state.is_constructed:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_establishment_read_permission(spicedb, eid, uid)
    else:
        await check_establishment_write_permission(spicedb, eid, uid)
    return agg


async def load_worker(nid: str, perm: str, uid: str | None) -> NPCWorkerAggregate:
    """Load worker aggregate and enforce Zanzibar read/write permissions."""
    repo = get_worker_repository()
    try:
        agg = await repo.load(to_uuid(nid))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Worker '{nid}' not found") from e
    if not agg.state.npc_id:
        raise HTTPException(status_code=404, detail=f"Worker '{nid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_npc_read_permission(spicedb, nid, uid)
    else:
        await check_npc_write_permission(spicedb, nid, uid)
    return agg
