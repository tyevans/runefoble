"""FastAPI router for procedural battlemap synthesis and geometry extraction."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.asset import BattlemapForged
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.asset_index import get_stored_asset
from runefoble_platform.event_sourcing import AggregateRepository
from runefoble_platform.storage import AssetNotFoundError, SiloStorageService

from asset_forge.aggregate import AssetForgeAggregate
from asset_forge.dependencies import (
    VerifiedUserId,
    get_forge_repo,
    get_principal,
    get_storage,
    publish_forge_event,
    record_asset_relations,
    require_asset_view,
    require_forge_permission,
)
from asset_forge.geometry import build_board_geometry_payload
from asset_forge.map_generation_engine import get_map_generator
from asset_forge.models import (
    BattlemapForgeRequest,
    BattlemapForgeResponse,
)
from asset_forge.raster.battlemap_raster import generate_battlemap_png
from asset_forge.silo_upload import store_forged_asset

router = APIRouter(
    prefix="/api/v1/forge/battlemap",
    tags=["Battlemap Forge"],
    dependencies=[Depends(get_principal)],
)


@router.post("", response_model=BattlemapForgeResponse)
async def forge_battlemap(
    request: BattlemapForgeRequest,
    user_id: VerifiedUserId,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> BattlemapForgeResponse:
    """Synthesize procedural battlemap texture, extract wall/hazard geometry, and store in Silo S3."""
    creator_id = user_id
    campaign_id = await require_forge_permission(user_id, request.campaign_id, spicedb)

    # 1. Layout through the MapGenerator port. No layout means no map is stored.
    # EngineUnavailableError becomes HTTP 503 in the app exception handler. Nothing is stored.
    generator = get_map_generator()
    layout = await generator.generate(
        prompt=request.prompt,
        width=request.width_cells,
        height=request.height_cells,
        seed=request.seed,
        wall_density=request.wall_density,
        hazard_density=request.hazard_density,
        theme_override=request.theme,
    )
    theme, wall_segments, hazard_cells, doors, grid = (
        layout.theme,
        layout.wall_segments,
        layout.hazard_cells,
        layout.doors,
        layout.grid,
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
    # Authorization relations first. A failed write raises AuthzError (HTTP 503) before storage.
    await record_asset_relations(spicedb, asset_id, creator_id, campaign_id)
    upload_meta = await store_forged_asset(
        storage,
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
    forge_agg = await load_or_create(repo, agg_id, AssetForgeAggregate)

    forge_agg.record_battlemap_forged(
        asset_id=asset_id,
        creator_id=creator_id,
        prompt=request.prompt,
        image_url=upload_meta["download_url"],
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
        image_url=upload_meta["download_url"],
        width_cells=request.width_cells,
        height_cells=request.height_cells,
        cell_size_px=request.cell_size_px,
        wall_segments_count=len(wall_segments),
        hazard_cells_count=len(hazard_cells),
        doors_count=len(doors),
        theme=theme,
    )
    await publish_forge_event(event)

    return BattlemapForgeResponse(
        asset_id=asset_id,
        image_url=upload_meta["download_url"],
        download_url=upload_meta["download_url"],
        width_cells=request.width_cells,
        height_cells=request.height_cells,
        cell_size_px=request.cell_size_px,
        theme=theme,
        wall_segments=wall_segments,
        hazard_cells=hazard_cells,
        doors=doors,
        board_geometry_payload=geometry_payload,
        generator=generator.generator_name,
        status="forged",
    )


@router.get("/{asset_id}", response_model=dict)
async def get_forged_battlemap(
    asset_id: str,
    user_id: VerifiedUserId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict:
    """Retrieve metadata for a previously forged battlemap. Requires `forged_asset.view`."""
    try:
        meta = await get_stored_asset(asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Battlemap asset '{asset_id}' not found."
        ) from exc
    await require_asset_view(spicedb, asset_id, user_id)
    return meta
