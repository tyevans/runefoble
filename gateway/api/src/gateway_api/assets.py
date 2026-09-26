"""Silo S3 media asset upload and management endpoints."""

from __future__ import annotations

import base64
import contextlib
import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from runefoble_events import AssetDeleted, AssetUploaded
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import EntityNotFoundError
from runefoble_platform.storage import (
    AssetNotFoundError,
    AssetValidationError,
    get_storage_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()
platform_settings = PlatformSettings()


class AssetUploadRequest(BaseModel):
    """JSON payload model for uploading media assets."""

    filename: str = Field(..., description="File name of the asset")
    content_type: str = Field(..., description="MIME content type (e.g. image/png)")
    data_base64: str = Field(..., description="Base64-encoded binary content")
    bucket: str | None = Field(default=None, description="Target Silo bucket")
    owner_id: str | None = Field(default=None, description="Asset owner user ID")
    asset_type: str = Field(
        default="avatar",
        description="Asset classification (avatar, battlemap, audio)",
    )


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


def _resolve_user_id(
    explicit: str | None,
    x_user_id: str | None,
    authorization: str | None,
) -> str:
    if explicit:
        return explicit
    if x_user_id:
        return x_user_id
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:].strip()
    return "user-default"


@router.post("/upload", response_model=AssetMetadataResponse)
async def upload_asset(
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
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
    explicit_owner: str | None = None
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

        explicit_owner = body.get("owner_id")
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
        explicit_owner = str(form.get("owner_id")) if "owner_id" in form else None
        bucket = str(form.get("bucket")) if "bucket" in form else None
        asset_type = str(form.get("asset_type", "avatar"))

    else:
        # Direct binary stream upload
        data = await request.body()
        content_type = ct_header.split(";")[0].strip()
        filename = request.query_params.get("filename", "upload.bin")
        explicit_owner = request.query_params.get("owner_id")
        bucket = request.query_params.get("bucket")
        asset_type = request.query_params.get("asset_type", "avatar")

    owner_id = _resolve_user_id(explicit_owner, x_user_id, authorization)
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
    except Exception as exc:
        logger.exception("Asset upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store media asset.") from exc

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
    storage_service = get_storage_service()
    try:
        if stream or download:
            data, content_type, meta = storage_service.get_asset_data_by_id(asset_id)
            disposition = "attachment" if download else "inline"
            fname = meta["object_key"].split("/")[-1]
            return Response(
                content=data,
                media_type=content_type,
                headers={"Content-Disposition": f'{disposition}; filename="{fname}"'},
            )

        meta = storage_service.get_asset_by_id(asset_id)
        resp = dict(meta)
        resp["download_url"] = f"/api/v1/assets/{asset_id}?stream=true"
        return resp
    except (AssetNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.") from exc


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
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """Delete asset from Silo storage and emit AssetDeleted domain event."""
    deleted_by = _resolve_user_id(None, x_user_id, authorization)
    storage_service = get_storage_service()

    try:
        meta = storage_service.get_asset_by_id(asset_id)
    except (AssetNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.") from exc

    storage_service.delete_asset_by_id(asset_id, deleted_by=deleted_by)

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
