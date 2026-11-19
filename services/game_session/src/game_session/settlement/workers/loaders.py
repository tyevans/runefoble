"""Data loaders and permission checks for the worker domain.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from fastapi import HTTPException
from game_session.dependencies import get_establishment_repository, get_worker_repository
from game_session.settlement.auth import (
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_npc_read_permission,
    check_npc_write_permission,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.worker_aggregate import NPCWorkerAggregate
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.identifiers import parse_uuid


async def load_establishment(eid: str, perm: str, uid: str | None) -> EstablishmentAggregate:
    """Load establishment aggregate and enforce Zanzibar read/write permissions."""
    repo = get_establishment_repository()
    try:
        agg = await repo.load(parse_uuid(eid, field="establishment_id"))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found") from e
    if not agg.state.is_constructed:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_establishment_read_permission(spicedb, eid, uid)
    else:
        await check_establishment_write_permission(spicedb, eid, uid, perm)
    return agg


async def load_worker(nid: str, perm: str, uid: str | None) -> NPCWorkerAggregate:
    """Load worker aggregate and enforce Zanzibar read/write permissions."""
    repo = get_worker_repository()
    try:
        agg = await repo.load(parse_uuid(nid, field="worker_id"))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Worker '{nid}' not found") from e
    if not agg.state.npc_id:
        raise HTTPException(status_code=404, detail=f"Worker '{nid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_npc_read_permission(spicedb, nid, uid)
    else:
        await check_npc_write_permission(spicedb, nid, uid, perm)
    return agg
