"""FastAPI router for procedural battlemap synthesis and geometry extraction."""

from __future__ import annotations

import contextlib
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.asset import BattlemapForged
from runefoble_platform.event_sourcing import AggregateRepository
from runefoble_platform.storage import SiloStorageService

from asset_forge.aggregate import AssetForgeAggregate
from asset_forge.dependencies import (
    check_user_can_forge,
    get_current_user_id,
    get_forge_repo,
    get_spicedb_client,
    get_storage,
    publish_forge_event,
)
from asset_forge.generator import generate_battlemap_png
from asset_forge.geometry import build_board_geometry_payload, generate_map_layout
from asset_forge.models import (
    BattlemapForgeRequest,
    BattlemapForgeResponse,
)

router = APIRouter(prefix="/api/v1/forge/battlemap", tags=["Battlemap Forge"])


@router.post("", response_model=BattlemapForgeResponse)
async def forge_battlemap(
    request: BattlemapForgeRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> BattlemapForgeResponse:
    """Synthesize procedural battlemap texture, extract wall/hazard geometry, and store in Silo S3."""
    creator_id = user_id or "anonymous_dm"

    # Zanzibar campaign authorization check
    if request.campaign_id:
        can_forge = await check_user_can_forge(user_id, request.campaign_id, spicedb)
        if not can_forge:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: User '{user_id}' does not have permission to forge maps for campaign '{request.campaign_id}'",
            )

    # 1. Procedural layout & geometry calculation
    theme, wall_segments, hazard_cells, doors, grid = generate_map_layout(
        prompt=request.prompt,
        width=request.width_cells,
        height=request.height_cells,
        wall_density=request.wall_density,
        hazard_density=request.hazard_density,
        theme_override=request.theme,
    )

    # 2. Raster map synthesis (standard valid PNG)
    png_bytes = generate_battlemap_png(
        grid=grid,
        theme=theme,
        cell_size_px=request.cell_size_px,
    )

    # 3. Store in Silo S3 media bucket
    asset_id = f"map-{uuid4().hex[:12]}"
    object_key = f"battlemaps/{asset_id}.png"
    upload_meta = storage.upload_asset(
        bucket=storage.default_bucket,
        object_key=object_key,
        data=png_bytes,
        content_type="image/png",
        owner_id=creator_id,
        asset_id=asset_id,
    )

    # 4. Spatial geometry projection payload for board_state
    geometry_payload = build_board_geometry_payload(wall_segments, hazard_cells, doors)

    # 5. Event-sourced aggregate persistence
    agg_id = request.campaign_id or uuid4()
    try:
        forge_agg = await repo.load(agg_id)
    except Exception:
        forge_agg = AssetForgeAggregate(agg_id)

    forge_agg.record_battlemap_forged(
        asset_id=asset_id,
        creator_id=creator_id,
        prompt=request.prompt,
        image_url=upload_meta["url"],
        width_cells=request.width_cells,
        height_cells=request.height_cells,
        cell_size_px=request.cell_size_px,
        wall_segments_count=len(wall_segments),
        hazard_cells_count=len(hazard_cells),
        doors_count=len(doors),
        theme=theme,
        campaign_id=request.campaign_id,
        session_id=request.session_id,
    )
    await repo.save(forge_agg)

    # 6. Publish domain event over Redis Streams & in-memory bus
    event = BattlemapForged(
        asset_id=asset_id,
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        creator_id=creator_id,
        prompt=request.prompt,
        image_url=upload_meta["url"],
        width_cells=request.width_cells,
        height_cells=request.height_cells,
        cell_size_px=request.cell_size_px,
        wall_segments_count=len(wall_segments),
        hazard_cells_count=len(hazard_cells),
        doors_count=len(doors),
        theme=theme,
    )
    await publish_forge_event(event)

    # 7. Write Zanzibar relationships to SpiceDB
    if user_id:
        with contextlib.suppress(Exception):
            await spicedb.write_relationship(
                resource_type="forged_asset",
                resource_id=asset_id,
                relation="creator",
                subject_type="user",
                subject_id=user_id,
            )
            if request.campaign_id:
                await spicedb.write_relationship(
                    resource_type="forged_asset",
                    resource_id=asset_id,
                    relation="campaign",
                    subject_type="campaign",
                    subject_id=str(request.campaign_id),
                )

    return BattlemapForgeResponse(
        asset_id=asset_id,
        image_url=upload_meta["url"],
        download_url=upload_meta["url"],
        width_cells=request.width_cells,
        height_cells=request.height_cells,
        cell_size_px=request.cell_size_px,
        theme=theme,
        wall_segments=wall_segments,
        hazard_cells=hazard_cells,
        doors=doors,
        board_geometry_payload=geometry_payload,
        status="forged",
    )


@router.get("/{asset_id}", response_model=dict)
async def get_forged_battlemap(
    asset_id: str,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
) -> dict:
    """Retrieve metadata for a previously forged battlemap."""
    try:
        return storage.get_asset_by_id(asset_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Battlemap asset '{asset_id}' not found."
        ) from exc
