"""Forge upload path: write to Silo first, index only after Silo confirms the write."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from runefoble_platform.asset_index import record_stored_asset
from runefoble_platform.storage import AssetStorageError, AssetValidationError, SiloStorageService


async def store_forged_asset(
    storage: SiloStorageService,
    *,
    object_key: str,
    data: bytes,
    content_type: str,
    owner_id: str,
    asset_id: str,
) -> dict[str, Any]:
    """Upload forged bytes to the default Silo bucket and record the asset index entry.

    Maps a rejected payload to HTTP 422 and any Silo failure to HTTP 503. On failure
    no index entry is written, so the caller never receives an asset id that does not
    resolve.
    """
    try:
        meta = storage.upload_asset(
            bucket=storage.default_bucket,
            object_key=object_key,
            data=data,
            content_type=content_type,
            owner_id=owner_id,
            asset_id=asset_id,
        )
    except AssetValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AssetStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail="Silo asset storage is unavailable. The asset was not stored.",
        ) from exc

    await record_stored_asset(meta)
    return meta
