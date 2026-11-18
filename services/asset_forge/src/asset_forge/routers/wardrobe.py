"""FastAPI router for generative character wardrobe and attire variant synthesis."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.character import PortraitVariantGenerated
from runefoble_platform.asset_index import get_stored_asset
from runefoble_platform.storage import AssetNotFoundError, SiloStorageService

from asset_forge.dependencies import (
    STREAM_CHARACTER,
    CallerId,
    get_principal,
    get_storage,
    get_wardrobe_generator,
    publish_forge_event,
    record_asset_relations,
    require_asset_view,
    require_forge_permission,
)
from asset_forge.models import WardrobeForgeRequest, WardrobeForgeResponse
from asset_forge.raster.wardrobe_raster import build_attire_prompt
from asset_forge.silo_upload import store_forged_asset
from asset_forge.wardrobe_generator import WardrobeGenerator, WardrobePortrait

router = APIRouter(
    prefix="/api/v1/forge/wardrobe", tags=["Wardrobe Forge"], dependencies=[Depends(get_principal)]
)


@router.post("", response_model=WardrobeForgeResponse)
async def forge_wardrobe_variant(
    request: WardrobeForgeRequest,
    user_id: CallerId,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    generator: Annotated[WardrobeGenerator, Depends(get_wardrobe_generator)],
) -> WardrobeForgeResponse:
    """Synthesize a wardrobe attire variant with the configured generator.

    The response names the generator and states whether it preserves the face.
    The default placeholder preserves no face.
    """
    creator_id = user_id
    campaign_id = await require_forge_permission(user_id, request.campaign_id, spicedb)

    # 1. Synthesize the image through the configured generator port
    final_prompt = build_attire_prompt(request.attire_type, request.prompt)
    png_bytes = generator.generate(
        WardrobePortrait(
            character_name=request.character_name,
            attire_type=request.attire_type,
            size_px=request.size_px,
            border_color_hex=request.border_color,
        ),
        final_prompt,
        request.face_embedding_seed,
    )

    # 2. Upload to Silo S3 object storage
    variant_id = f"var-{uuid4().hex[:10]}"
    object_key = f"wardrobe/{variant_id}.png"
    # Authorization relations first. A failed write raises AuthzError (HTTP 503) before storage.
    await record_asset_relations(spicedb, variant_id, creator_id, campaign_id)
    upload_meta = await store_forged_asset(
        storage,
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
        image_url=upload_meta["download_url"],
        prompt=final_prompt,
        is_active=False,
    )
    await publish_forge_event(event, stream=STREAM_CHARACTER)

    return WardrobeForgeResponse(
        variant_id=variant_id,
        character_id=str(request.character_id),
        variant_name=f"{request.character_name} - {request.attire_type.replace('_', ' ').title()}",
        attire_type=request.attire_type,
        image_url=upload_meta["download_url"],
        download_url=upload_meta["download_url"],
        prompt=final_prompt,
        generator=generator.name,
        preserves_face=generator.preserves_face,
        status="forged",
    )


@router.get("/{variant_id}", response_model=dict)
async def get_forged_wardrobe_variant(
    variant_id: str,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict:
    """Retrieve metadata for a forged wardrobe attire variant. Requires `forged_asset.view`."""
    try:
        meta = await get_stored_asset(variant_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Wardrobe variant '{variant_id}' not found."
        ) from exc
    await require_asset_view(spicedb, variant_id, user_id)
    return meta
