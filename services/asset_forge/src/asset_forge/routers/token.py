"""FastAPI router for procedural character and monster token portrait synthesis."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.events import TokenAssetForged
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.asset_index import get_stored_asset
from runefoble_platform.event_sourcing import AggregateRepository
from runefoble_platform.storage import AssetNotFoundError, SiloStorageService

from asset_forge.aggregate import AssetForgeAggregate
from asset_forge.dependencies import (
    CallerId,
    get_forge_repo,
    get_principal,
    get_storage,
    publish_forge_event,
    record_asset_relations,
    require_asset_view,
    require_forge_permission,
)
from asset_forge.models import (
    TokenForgeRequest,
    TokenForgeResponse,
)
from asset_forge.raster.token_raster import generate_token_portrait_png
from asset_forge.silo_upload import store_forged_asset

router = APIRouter(
    prefix="/api/v1/forge/token", tags=["Token Forge"], dependencies=[Depends(get_principal)]
)


@router.post("", response_model=TokenForgeResponse)
async def forge_token(
    request: TokenForgeRequest,
    user_id: CallerId,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> TokenForgeResponse:
    """Synthesize cropped circular token portrait with transparency and store in Silo S3."""
    creator_id = user_id
    campaign_id = await require_forge_permission(user_id, request.campaign_id, spicedb)

    # 1. Synthesize circular token portrait PNG with alpha transparency
    png_bytes = generate_token_portrait_png(
        token_name=request.token_name,
        prompt=request.prompt,
        token_type=request.token_type,
        size_px=request.size_px,
        crop_style=request.crop_style,
        border_color_hex=request.border_color,
        border_width=request.border_width,
        transparent_background=request.transparent_background,
    )

    # 2. Upload to Silo S3 object storage
    asset_id = f"tok-{uuid4().hex[:12]}"
    object_key = f"tokens/{asset_id}.png"
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

    # 3. Record domain event in event-sourced aggregate
    # The campaign id is the forge aggregate id. The campaign record list reads it back.
    forge_agg = await load_or_create(repo, campaign_id, AssetForgeAggregate)

    forge_agg.record_token_forged(
        asset_id=asset_id,
        creator_id=creator_id,
        prompt=request.prompt,
        token_name=request.token_name,
        token_type=request.token_type,
        image_url=upload_meta["download_url"],
        crop_style=request.crop_style,
        transparent_background=request.transparent_background,
        campaign_id=request.campaign_id,
    )
    await repo.save(forge_agg)

    # 4. Dispatch domain event to Redis Streams and local bus
    event = TokenAssetForged(
        asset_id=asset_id,
        campaign_id=request.campaign_id,
        creator_id=creator_id,
        prompt=request.prompt,
        token_name=request.token_name,
        token_type=request.token_type,
        image_url=upload_meta["download_url"],
        crop_style=request.crop_style,
        transparent_background=request.transparent_background,
    )
    await publish_forge_event(event)

    return TokenForgeResponse(
        asset_id=asset_id,
        image_url=upload_meta["download_url"],
        download_url=upload_meta["download_url"],
        token_name=request.token_name,
        token_type=request.token_type,
        crop_style=request.crop_style,
        size_px=request.size_px,
        has_transparency=request.transparent_background,
        status="forged",
    )


@router.get("/{asset_id}", response_model=dict)
async def get_forged_token(
    asset_id: str,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict:
    """Retrieve metadata for a previously forged token portrait. Requires `forged_asset.view`."""
    try:
        meta = await get_stored_asset(asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Token asset '{asset_id}' not found.") from exc
    await require_asset_view(spicedb, asset_id, user_id)
    return meta
