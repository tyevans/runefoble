"""FastAPI router for procedural character and monster token portrait synthesis."""

from __future__ import annotations

import contextlib
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.asset import TokenAssetForged
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
from asset_forge.generator import generate_token_portrait_png
from asset_forge.models import (
    TokenForgeRequest,
    TokenForgeResponse,
)

router = APIRouter(prefix="/api/v1/forge/token", tags=["Token Forge"])


@router.post("", response_model=TokenForgeResponse)
async def forge_token(
    request: TokenForgeRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> TokenForgeResponse:
    """Synthesize cropped circular token portrait with transparency and store in Silo S3."""
    creator_id = user_id or "anonymous_creator"

    # Zanzibar campaign authorization check
    if request.campaign_id:
        can_forge = await check_user_can_forge(user_id, request.campaign_id, spicedb)
        if not can_forge:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: User '{user_id}' does not have permission to forge tokens for campaign '{request.campaign_id}'",
            )

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
    upload_meta = storage.upload_asset(
        bucket=storage.default_bucket,
        object_key=object_key,
        data=png_bytes,
        content_type="image/png",
        owner_id=creator_id,
        asset_id=asset_id,
    )

    # 3. Record domain event in event-sourced aggregate
    agg_id = request.campaign_id or uuid4()
    try:
        forge_agg = await repo.load(agg_id)
    except Exception:
        forge_agg = AssetForgeAggregate(agg_id)

    forge_agg.record_token_forged(
        asset_id=asset_id,
        creator_id=creator_id,
        prompt=request.prompt,
        token_name=request.token_name,
        token_type=request.token_type,
        image_url=upload_meta["url"],
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
        image_url=upload_meta["url"],
        crop_style=request.crop_style,
        transparent_background=request.transparent_background,
    )
    await publish_forge_event(event)

    # 5. Write Zanzibar relationships to SpiceDB
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

    return TokenForgeResponse(
        asset_id=asset_id,
        image_url=upload_meta["url"],
        download_url=upload_meta["url"],
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
    storage: Annotated[SiloStorageService, Depends(get_storage)],
) -> dict:
    """Retrieve metadata for a previously forged token portrait."""
    try:
        return storage.get_asset_by_id(asset_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Token asset '{asset_id}' not found.") from exc
