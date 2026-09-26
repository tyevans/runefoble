"""Silo S3-compatible media asset storage service."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import EntityNotFoundError, RunefobleError

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/svg+xml",
        "audio/wav",
        "audio/mpeg",
    }
)

MAX_ASSET_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB


class AssetStorageError(RunefobleError):
    """Raised when an asset storage operation fails."""


class AssetValidationError(AssetStorageError):
    """Raised when an asset violates size or MIME type restrictions."""


class AssetNotFoundError(EntityNotFoundError):
    """Raised when an asset is not found in storage."""

    def __init__(self, asset_ref: str):
        super().__init__(entity_type="Asset", entity_id=asset_ref)


class SiloStorageService:
    """S3-compatible object storage service for Silo (MinIO fork).

    Provides media asset uploads, retrieval, presigned URL generation,
    and automatic in-memory mock fallback when the remote Silo daemon is offline.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket_assets: str | None = None,
        secure: bool | None = None,
        force_mock: bool = False,
    ) -> None:
        settings = PlatformSettings()
        raw_endpoint = endpoint or settings.silo_endpoint
        self.secure = secure if secure is not None else settings.silo_secure
        self.access_key = access_key or settings.silo_access_key
        self.secret_key = secret_key or settings.silo_secret_key
        self.default_bucket = bucket_assets or settings.silo_bucket_assets
        self.force_mock = force_mock

        if raw_endpoint.startswith("http://") or raw_endpoint.startswith("https://"):
            self.base_url = raw_endpoint.rstrip("/")
        else:
            scheme = "https" if self.secure else "http"
            self.base_url = f"{scheme}://{raw_endpoint.lstrip('/')}"

        # In-memory storage structures for offline mock fallback
        # Key: "{bucket}/{object_key}" -> (data_bytes, content_type, metadata_dict)
        self._memory_store: dict[str, tuple[bytes, str, dict[str, Any]]] = {}
        # Key: asset_id -> metadata_dict
        self._asset_index: dict[str, dict[str, Any]] = {}

    def validate_asset(self, data: bytes, content_type: str) -> None:
        """Validate media payload MIME type and file size."""
        if not data:
            raise AssetValidationError("Asset payload cannot be empty.")

        if content_type not in ALLOWED_MIME_TYPES:
            raise AssetValidationError(
                f"Unsupported media MIME type: '{content_type}'. "
                f"Allowed types: {sorted(ALLOWED_MIME_TYPES)}"
            )

        if len(data) > MAX_ASSET_SIZE_BYTES:
            raise AssetValidationError(
                f"Asset size ({len(data)} bytes) exceeds the maximum allowed "
                f"limit of {MAX_ASSET_SIZE_BYTES} bytes (10MB)."
            )

    def generate_presigned_url(self, bucket: str, object_key: str, expires_in: int = 3600) -> str:
        """Generate a public or presigned access URL for an object."""
        return f"{self.base_url}/{bucket}/{object_key}?expires={expires_in}"

    def upload_asset(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str,
        owner_id: str,
        asset_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload media bytes to Silo storage or in-memory fallback.

        Validates MIME type and size, writes data, and returns metadata.
        """
        self.validate_asset(data=data, content_type=content_type)

        aid = asset_id or str(uuid4())
        url = self.generate_presigned_url(bucket=bucket, object_key=object_key)
        created_at = datetime.now(UTC).isoformat()

        metadata: dict[str, Any] = {
            "asset_id": aid,
            "bucket": bucket,
            "object_key": object_key,
            "content_type": content_type,
            "byte_size": len(data),
            "owner_id": owner_id,
            "url": url,
            "created_at": created_at,
        }

        # Attempt remote Silo PUT if not forcing mock
        if not self.force_mock:
            try:
                target_url = f"{self.base_url}/{bucket}/{object_key}"
                with httpx.Client(timeout=1.5) as client:
                    resp = client.put(
                        target_url,
                        content=data,
                        headers={"Content-Type": content_type},
                    )
                    if resp.status_code not in (200, 201, 204):
                        logger.warning(
                            "Silo remote returned status %d. Falling back to in-memory store.",
                            resp.status_code,
                        )
            except Exception as exc:
                logger.debug(
                    "Remote Silo unreachable (%s). Using robust in-memory mock fallback.",
                    exc,
                )

        # Store in memory cache / fallback
        store_key = f"{bucket}/{object_key}"
        self._memory_store[store_key] = (data, content_type, metadata)
        self._asset_index[aid] = metadata

        return metadata

    def get_asset(self, bucket: str, object_key: str) -> tuple[bytes, str]:
        """Retrieve asset binary content and content-type."""
        store_key = f"{bucket}/{object_key}"
        if store_key in self._memory_store:
            data, content_type, _ = self._memory_store[store_key]
            return data, content_type

        if not self.force_mock:
            try:
                target_url = f"{self.base_url}/{bucket}/{object_key}"
                with httpx.Client(timeout=1.5) as client:
                    resp = client.get(target_url)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("Content-Type", "application/octet-stream")
                        return resp.content, content_type
            except Exception as exc:
                logger.debug("Failed remote GET from Silo (%s)", exc)

        raise AssetNotFoundError(store_key)

    def get_asset_by_id(self, asset_id: str) -> dict[str, Any]:
        """Retrieve metadata for an asset by asset_id."""
        if asset_id not in self._asset_index:
            raise AssetNotFoundError(asset_id)
        return self._asset_index[asset_id]

    def get_asset_data_by_id(self, asset_id: str) -> tuple[bytes, str, dict[str, Any]]:
        """Retrieve binary data, content-type, and metadata by asset_id."""
        meta = self.get_asset_by_id(asset_id)
        data, content_type = self.get_asset(meta["bucket"], meta["object_key"])
        return data, content_type, meta

    def delete_asset(self, bucket: str, object_key: str, deleted_by: str) -> bool:
        """Delete an asset from storage."""
        store_key = f"{bucket}/{object_key}"
        deleted = False

        if store_key in self._memory_store:
            _, _, meta = self._memory_store.pop(store_key)
            self._asset_index.pop(meta.get("asset_id", ""), None)
            deleted = True

        if not self.force_mock:
            try:
                target_url = f"{self.base_url}/{bucket}/{object_key}"
                with httpx.Client(timeout=1.5) as client:
                    resp = client.delete(target_url)
                    if resp.status_code in (200, 204):
                        deleted = True
            except Exception as exc:
                logger.debug("Failed remote DELETE from Silo (%s)", exc)

        return deleted

    def delete_asset_by_id(self, asset_id: str, deleted_by: str) -> bool:
        """Delete an asset given its asset_id."""
        meta = self.get_asset_by_id(asset_id)
        return self.delete_asset(meta["bucket"], meta["object_key"], deleted_by)

    def clear(self) -> None:
        """Clear in-memory mock storage (useful for test isolation)."""
        self._memory_store.clear()
        self._asset_index.clear()


_global_storage_service: SiloStorageService | None = None


def get_storage_service() -> SiloStorageService:
    """Get the active SiloStorageService instance."""
    global _global_storage_service
    if _global_storage_service is None:
        _global_storage_service = SiloStorageService()
    return _global_storage_service


def set_storage_service(service: SiloStorageService | None) -> None:
    """Set or override the active SiloStorageService instance."""
    global _global_storage_service
    _global_storage_service = service
