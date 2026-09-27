"""FastAPI router for generative character wardrobe and attire variant synthesis."""

from __future__ import annotations

import contextlib
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.character import PortraitVariantGenerated
from runefoble_platform.storage import SiloStorageService

from asset_forge.dependencies import (
    check_user_can_forge,
    get_current_user_id,
    get_spicedb_client,
    get_storage,
    publish_forge_event,
)
from asset_forge.generator import generate_wardrobe_portrait_png
from asset_forge.models import WardrobeForgeRequest, WardrobeForgeResponse

router = APIRouter(prefix="/api/v1/forge/wardrobe", tags=["Wardrobe Forge"])


@router.post("", response_model=WardrobeForgeResponse)
@router.post("/generate", response_model=WardrobeForgeResponse)
async def forge_wardrobe_variant(
    request: WardrobeForgeRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> WardrobeForgeResponse:
    """Synthesize stylistic narrative wardrobe attire variation preserving character facial identity."""
    creator_id = user_id or "anonymous_creator"

    # Zanzibar campaign authorization check
    if request.campaign_id:
        can_forge = await check_user_can_forge(user_id, request.campaign_id, spicedb)
        if not can_forge:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: User '{user_id}' does not have permission to forge wardrobe for campaign '{request.campaign_id}'",
            )

    # 1. Synthesize PNG raster preserving facial embedding seed
    png_bytes, final_prompt = generate_wardrobe_portrait_png(
        character_name=request.character_name,
        attire_type=request.attire_type,
        custom_prompt=request.prompt,
        face_seed=request.face_embedding_seed,
        size_px=request.size_px,
        border_color_hex=request.border_color,
    )

    # 2. Upload to Silo S3 object storage
    variant_id = f"var-{uuid4().hex[:10]}"
    object_key = f"wardrobe/{variant_id}.png"
    upload_meta = storage.upload_asset(
        bucket=storage.default_bucket,
        object_key=object_key,
        data=png_bytes,
        content_type="image/png",
        owner_id=creator_id,
        asset_id=variant_id,
    )

    # 3. Publish PortraitVariantGenerated domain event over Redis Streams / event bus
    event = PortraitVariantGenerated(
        character_id=str(request.character_id),
        variant_id=variant_id,
        variant_name=f"{request.character_name} - {request.attire_type.replace('_', ' ').title()}",
        attire_type=request.attire_type,
        image_url=upload_meta["url"],
        prompt=final_prompt,
        is_active=False,
    )
    await publish_forge_event(event)

    # 4. Write Zanzibar relationships to SpiceDB
    if user_id:
        with contextlib.suppress(Exception):
            await spicedb.write_relationship(
                resource_type="forged_asset",
                resource_id=variant_id,
                relation="creator",
                subject_type="user",
                subject_id=user_id,
            )
            if request.campaign_id:
                await spicedb.write_relationship(
                    resource_type="forged_asset",
                    resource_id=variant_id,
                    relation="campaign",
                    subject_type="campaign",
                    subject_id=str(request.campaign_id),
                )

    return WardrobeForgeResponse(
        variant_id=variant_id,
        character_id=str(request.character_id),
        variant_name=f"{request.character_name} - {request.attire_type.replace('_', ' ').title()}",
        attire_type=request.attire_type,
        image_url=upload_meta["url"],
        download_url=upload_meta["url"],
        prompt=final_prompt,
        status="forged",
    )


@router.get("/{variant_id}", response_model=dict)
async def get_forged_wardrobe_variant(
    variant_id: str,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
) -> dict:
    """Retrieve metadata for a previously forged wardrobe attire variant."""
    try:
        return storage.get_asset_by_id(variant_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Wardrobe variant '{variant_id}' not found."
        ) from exc
