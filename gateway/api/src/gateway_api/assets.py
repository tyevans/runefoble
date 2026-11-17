"""Silo S3 media asset upload and management endpoints."""

from __future__ import annotations

import base64
import contextlib
import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Response
from gateway_api.auth import CurrentPrincipal
from pydantic import BaseModel
from runefoble_events import AssetDeleted, AssetUploaded
from runefoble_platform.asset_index import (
    get_stored_asset,
    record_stored_asset,
    remove_stored_asset,
)
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.storage import (
    AssetNotFoundError,
    AssetStorageError,
    AssetValidationError,
    get_storage_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()
platform_settings = PlatformSettings()


class AssetMetadataResponse(BaseModel):
    """Response model representing stored media asset metadata."""

    asset_id: str
    bucket: str
    object_key: str
    content_type: str
    byte_size: int
    owner_id: str
    url: str
    download_url: str
    created_at: str


class AssetDeleteResponse(BaseModel):
    """Response model returned when an asset is deleted."""

    deleted: bool
    asset_id: str
    deleted_by: str


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    return cleaned or "asset.bin"


@router.post("/upload", response_model=AssetMetadataResponse)
async def upload_asset(
    request: Request,
    principal: CurrentPrincipal,
) -> dict[str, Any]:
    """Upload media assets (avatars, battlemaps, audio) to Silo S3 storage.

    Supports multipart/form-data or JSON payloads with base64 data.
    Validates MIME type and file size limits, publishes AssetUploaded event,
    and returns asset metadata.
    """
    ct_header = request.headers.get("content-type", "")
    filename = "upload.bin"
    content_type = ""
    data: bytes = b""
    bucket: str | None = None
    asset_type: str = "avatar"

    if "application/json" in ct_header:
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Malformed JSON body: {exc}") from exc

        filename = body.get("filename", "upload.bin")
        content_type = body.get("content_type", "")
        b64_str = body.get("data_base64", "")
        if not b64_str:
            raise HTTPException(status_code=400, detail="Missing required 'data_base64' field.")
        try:
            data = base64.b64decode(b64_str)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {exc}") from exc

        bucket = body.get("bucket")
        asset_type = body.get("asset_type", "avatar")

    elif "multipart/form-data" in ct_header:
        form = await request.form()
        upload_file = form.get("file")
        if not upload_file or not hasattr(upload_file, "read"):
            raise HTTPException(
                status_code=400, detail="Missing 'file' field in multipart/form-data payload."
            )
        data = await upload_file.read()
        filename = getattr(upload_file, "filename", None) or "upload.bin"
        content_type = getattr(upload_file, "content_type", None) or str(
            form.get("content_type", "")
        )
        bucket = str(form.get("bucket")) if "bucket" in form else None
        asset_type = str(form.get("asset_type", "avatar"))

    else:
        # Direct binary stream upload
        data = await request.body()
        content_type = ct_header.split(";")[0].strip()
        filename = request.query_params.get("filename", "upload.bin")
        bucket = request.query_params.get("bucket")
        asset_type = request.query_params.get("asset_type", "avatar")

    owner_id = principal.user_id
    target_bucket = bucket or platform_settings.silo_bucket_assets
    safe_name = _sanitize_filename(filename)
    object_key = f"{asset_type}s/{uuid4().hex[:10]}_{safe_name}"

    storage_service = get_storage_service()
    try:
        meta = storage_service.upload_asset(
            bucket=target_bucket,
            object_key=object_key,
            data=data,
            content_type=content_type,
            owner_id=owner_id,
        )
    except (AssetValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AssetStorageError as exc:
        logger.error("Silo rejected asset upload: %s", exc)
        raise HTTPException(
            status_code=503, detail="Silo asset storage is unavailable. The asset was not stored."
        ) from exc
    except Exception as exc:
        logger.exception("Asset upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store media asset.") from exc

    await record_stored_asset(meta)

    # Publish AssetUploaded domain event
    event = AssetUploaded(
        asset_id=meta["asset_id"],
        bucket=meta["bucket"],
        object_key=meta["object_key"],
        content_type=meta["content_type"],
        byte_size=meta["byte_size"],
        owner_id=meta["owner_id"],
        url=meta["url"],
    )

    # Dispatched via Redis event bus if gateway has it configured
    from gateway_api.main import get_event_bus

    bus = get_event_bus()
    if bus is not None:
        with contextlib.suppress(Exception):
            await bus.publish_event("runefoble.events.asset", event)

    # Dispatched via platform in-memory bus
    with contextlib.suppress(Exception):
        await platform_bus.publish("runefoble.events.asset.uploaded", event)

    meta_copy = dict(meta)
    meta_copy["download_url"] = f"/api/v1/assets/{meta['asset_id']}?stream=true"
    return meta_copy


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    stream: bool = Query(False, description="Stream raw media content directly"),
    download: bool = Query(False, description="Force download attachment"),
):
    """Retrieve asset metadata or stream binary content."""
    try:
        meta = await get_stored_asset(asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.") from exc

    if stream or download:
        try:
            data, content_type = get_storage_service().get_asset(meta["bucket"], meta["object_key"])
        except AssetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.") from exc
        except AssetStorageError as exc:
            raise HTTPException(
                status_code=503, detail="Silo asset storage is unavailable."
            ) from exc
        disposition = "attachment" if download else "inline"
        fname = meta["object_key"].split("/")[-1]
        return Response(
            content=data,
            media_type=content_type,
            headers={"Content-Disposition": f'{disposition}; filename="{fname}"'},
        )

    resp = dict(meta)
    resp["download_url"] = f"/api/v1/assets/{asset_id}?stream=true"
    return resp


@router.get("/{asset_id}/stream")
async def stream_asset(asset_id: str):
    """Direct streaming endpoint for media assets (images, audio)."""
    return await get_asset(asset_id, stream=True, download=False)


@router.get("/{asset_id}/download")
async def download_asset(asset_id: str):
    """Direct download endpoint with attachment Content-Disposition."""
    return await get_asset(asset_id, stream=False, download=True)


@router.delete("/{asset_id}", response_model=AssetDeleteResponse)
async def delete_asset(
    asset_id: str,
    principal: CurrentPrincipal,
) -> dict[str, Any]:
    """Delete asset from Silo storage and emit AssetDeleted domain event."""
    deleted_by = principal.user_id

    try:
        meta = await get_stored_asset(asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.") from exc

    try:
        get_storage_service().delete_asset(meta["bucket"], meta["object_key"])
    except AssetNotFoundError:
        # Silo no longer holds the object. Drop the stale index entry below.
        logger.warning("Asset '%s' was missing in Silo. Removing its index entry.", asset_id)
    except AssetStorageError as exc:
        raise HTTPException(
            status_code=503, detail="Silo asset storage is unavailable. The asset was not deleted."
        ) from exc

    await remove_stored_asset(asset_id, deleted_by=deleted_by)

    # Publish AssetDeleted domain event
    delete_event = AssetDeleted(
        asset_id=asset_id,
        bucket=meta["bucket"],
        object_key=meta["object_key"],
        deleted_by=deleted_by,
    )

    from gateway_api.main import get_event_bus

    bus = get_event_bus()
    if bus is not None:
        with contextlib.suppress(Exception):
            await bus.publish_event("runefoble.events.asset", delete_event)

    with contextlib.suppress(Exception):
        await platform_bus.publish("runefoble.events.asset.deleted", delete_event)

    return {
        "deleted": True,
        "asset_id": asset_id,
        "deleted_by": deleted_by,
    }
