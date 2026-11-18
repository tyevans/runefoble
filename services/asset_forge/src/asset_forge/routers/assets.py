"""Silo media asset routes: upload, read, stream, download and delete (TASK-0595).

These routes moved from the gateway. The gateway proxies them. Upload, read and delete need a
verified bearer token. Reads also need `forged_asset.view`. A browser fetches reads with the
bearer and shows them through a blob URL (TASK-0784).
Governed by ADR-0001 (SpiceDB object authorization), ADR-0007 and ADR-0015 (c).
"""

from __future__ import annotations

import logging
import re
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.events import AssetDeleted, AssetUploaded
from runefoble_platform.asset_index import (
    get_stored_asset,
    record_stored_asset,
    remove_stored_asset,
)
from runefoble_platform.config import PlatformSettings
from runefoble_platform.storage import (
    AssetNotFoundError,
    AssetStorageError,
    AssetValidationError,
    SiloStorageService,
)

from asset_forge.asset_authz import (
    require_asset_permission,
    require_campaign_play,
    revoke_asset_ownership,
    write_asset_ownership,
)
from asset_forge.asset_upload import parse_asset_upload
from asset_forge.dependencies import STREAM_ASSET, get_principal, get_storage, publish_forge_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])
platform_settings = PlatformSettings()

Principal = Annotated[VerifiedPrincipal, Depends(get_principal)]
Storage = Annotated[SiloStorageService, Depends(get_storage)]
Spicedb = Annotated[SpiceDBClient, Depends(get_spicedb_client)]


class AssetMetadataResponse(BaseModel):
    """Stored media asset metadata."""

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
    """Returned when an asset is deleted."""

    deleted: bool
    asset_id: str
    deleted_by: str


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    return cleaned or "asset.bin"


def _not_found(asset_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")


@router.post("/upload", response_model=AssetMetadataResponse)
async def upload_asset(
    request: Request,
    principal: Principal,
    storage: Storage,
    spicedb: Spicedb,
) -> dict[str, Any]:
    """Upload an avatar, battlemap or audio file to Silo. Publishes AssetUploaded."""
    upload = await parse_asset_upload(request)
    owner_id = principal.user_id
    if upload.campaign_id:
        await require_campaign_play(spicedb, owner_id, upload.campaign_id)
    target_bucket = upload.bucket or platform_settings.silo_bucket_assets
    object_key = f"{upload.asset_type}s/{uuid4().hex[:10]}_{_sanitize_filename(upload.filename)}"

    try:
        meta = storage.upload_asset(
            bucket=target_bucket,
            object_key=object_key,
            data=upload.data,
            content_type=upload.content_type,
            owner_id=owner_id,
        )
    except (AssetValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AssetStorageError as exc:
        logger.error("Silo rejected asset upload: %s", exc)
        raise HTTPException(
            status_code=503, detail="Silo asset storage is unavailable. The asset was not stored."
        ) from exc

    try:
        await write_asset_ownership(spicedb, meta["asset_id"], owner_id, upload.campaign_id)
    except HTTPException:
        # No owner tuple means nobody could manage the object. Remove it.
        try:
            storage.delete_asset(meta["bucket"], meta["object_key"])
        except AssetStorageError:
            logger.exception(
                "Asset '%s' could not be removed after a failed owner write", meta["asset_id"]
            )
        raise

    await record_stored_asset(meta)
    await publish_forge_event(
        AssetUploaded(
            asset_id=meta["asset_id"],
            bucket=meta["bucket"],
            object_key=meta["object_key"],
            content_type=meta["content_type"],
            byte_size=meta["byte_size"],
            owner_id=meta["owner_id"],
            url=meta["url"],
        ),
        stream=STREAM_ASSET,
    )

    meta_copy = dict(meta)
    meta_copy["download_url"] = f"/api/v1/assets/{meta['asset_id']}?stream=true"
    return meta_copy


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    principal: Principal,
    storage: Storage,
    spicedb: Spicedb,
    stream: bool = Query(False, description="Stream raw media content directly"),
    download: bool = Query(False, description="Force download attachment"),
) -> Any:
    """Return asset metadata, or the raw bytes when `stream` or `download` is set.

    Needs `forged_asset.view`.
    """
    meta = await _viewable_asset(asset_id, principal, spicedb)

    if stream or download:
        return _binary_response(storage, asset_id, meta, download=download)

    resp = dict(meta)
    resp["download_url"] = f"/api/v1/assets/{asset_id}?stream=true"
    return resp


@router.get("/{asset_id}/stream")
async def stream_asset(
    asset_id: str, principal: Principal, storage: Storage, spicedb: Spicedb
) -> Response:
    """Stream the raw bytes of an asset inline. Needs `forged_asset.view`."""
    meta = await _viewable_asset(asset_id, principal, spicedb)
    return _binary_response(storage, asset_id, meta, download=False)


@router.get("/{asset_id}/download")
async def download_asset(
    asset_id: str, principal: Principal, storage: Storage, spicedb: Spicedb
) -> Response:
    """Download the raw bytes of an asset as an attachment. Needs `forged_asset.view`."""
    meta = await _viewable_asset(asset_id, principal, spicedb)
    return _binary_response(storage, asset_id, meta, download=True)


async def _viewable_asset(
    asset_id: str, principal: VerifiedPrincipal, spicedb: SpiceDBClient
) -> dict[str, Any]:
    """Return the stored asset metadata when the principal can view the asset."""
    try:
        meta = await get_stored_asset(asset_id)
    except AssetNotFoundError as exc:
        raise _not_found(asset_id) from exc
    await require_asset_permission(spicedb, principal.user_id, asset_id, "view")
    return meta


def _binary_response(
    storage: SiloStorageService, asset_id: str, meta: dict[str, Any], *, download: bool
) -> Response:
    try:
        data, content_type = storage.get_asset(meta["bucket"], meta["object_key"])
    except AssetNotFoundError as exc:
        raise _not_found(asset_id) from exc
    except AssetStorageError as exc:
        raise HTTPException(status_code=503, detail="Silo asset storage is unavailable.") from exc
    disposition = "attachment" if download else "inline"
    fname = meta["object_key"].split("/")[-1]
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'{disposition}; filename="{fname}"'},
    )


@router.delete("/{asset_id}", response_model=AssetDeleteResponse)
async def delete_asset(
    asset_id: str,
    principal: Principal,
    storage: Storage,
    spicedb: Spicedb,
) -> dict[str, Any]:
    """Delete an asset from Silo and publish AssetDeleted. Needs `forged_asset.manage`."""
    deleted_by = principal.user_id
    try:
        meta = await get_stored_asset(asset_id)
    except AssetNotFoundError as exc:
        raise _not_found(asset_id) from exc
    await require_asset_permission(spicedb, deleted_by, asset_id, "manage")

    try:
        storage.delete_asset(meta["bucket"], meta["object_key"])
    except AssetNotFoundError:
        # Silo no longer holds the object. Drop the stale index entry below.
        logger.warning("Asset '%s' was missing in Silo. Removing its index entry.", asset_id)
    except AssetStorageError as exc:
        raise HTTPException(
            status_code=503, detail="Silo asset storage is unavailable. The asset was not deleted."
        ) from exc

    await remove_stored_asset(asset_id, deleted_by=deleted_by)
    await revoke_asset_ownership(spicedb, asset_id)
    await publish_forge_event(
        AssetDeleted(
            asset_id=asset_id,
            bucket=meta["bucket"],
            object_key=meta["object_key"],
            deleted_by=deleted_by,
        ),
        stream=STREAM_ASSET,
    )
    return {"deleted": True, "asset_id": asset_id, "deleted_by": deleted_by}
