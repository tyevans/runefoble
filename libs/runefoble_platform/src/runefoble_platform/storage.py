"""Silo S3-compatible media asset storage service.

Writes and reads go straight to the Silo daemon. There is no in-memory fallback.
Every request carries an AWS Signature Version 4 signature (TASK-0926). A failed Silo
request raises AssetStorageError, so callers never report success for bytes that Silo
did not store.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import ConfigurationError, EntityNotFoundError, RunefobleError
from runefoble_platform.silo_signing import sigv4_headers

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/svg+xml",
        "audio/wav",
        "audio/mpeg",
        "application/pdf",
        "model/stl",
        "application/sla",
    }
)


MAX_ASSET_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

SILO_TIMEOUT_SECONDS: float = 1.5

ACCESS_KEY_VAR = "RUNEFOBLE_SILO_ACCESS_KEY"
SECRET_KEY_VAR = "RUNEFOBLE_SILO_SECRET_KEY"


class AssetStorageError(RunefobleError):
    """Raised when an asset storage operation fails.

    `bucket` and `object_key` name the Silo object when the failure is a Silo request.
    They are None for a payload that was rejected before any request.
    """

    def __init__(
        self, message: str, *, bucket: str | None = None, object_key: str | None = None
    ) -> None:
        super().__init__(message, {"bucket": bucket, "object_key": object_key})
        self.bucket = bucket
        self.object_key = object_key


class AssetValidationError(AssetStorageError):
    """Raised when an asset violates size or MIME type restrictions."""


class AssetNotFoundError(EntityNotFoundError):
    """Raised when an asset is not found in storage."""

    def __init__(self, asset_ref: str):
        super().__init__(entity_type="Asset", entity_id=asset_ref)


class SiloStorageService:
    """S3-compatible object storage client for Silo (MinIO fork).

    Provides media asset uploads, retrieval, and deletion. It never returns a Silo object
    URL to a caller. Reads go through the authorized asset routes (ADR-0001, ADR-0015).
    Each request is signed with SigV4 (service ``s3``, region ``silo_region``). In a deployed
    environment, missing keys raise ConfigurationError at construction. Elsewhere, each
    request then raises AssetStorageError that names the missing setting.
    The optional ``transport`` argument injects an httpx transport. Tests use it to
    stand in for the Silo HTTP boundary. Production code never sets it.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket_assets: str | None = None,
        secure: bool | None = None,
        transport: httpx.BaseTransport | None = None,
        region: str | None = None,
    ) -> None:
        settings = PlatformSettings()
        raw_endpoint = endpoint or settings.silo_endpoint
        self.secure = secure if secure is not None else settings.silo_secure
        self.access_key = access_key or settings.silo_access_key
        self.secret_key = secret_key or settings.silo_secret_key
        self.default_bucket = bucket_assets or settings.silo_bucket_assets
        self.region = region or settings.silo_region
        self._transport = transport

        if raw_endpoint.startswith("http://") or raw_endpoint.startswith("https://"):
            self.base_url = raw_endpoint.rstrip("/")
        else:
            scheme = "https" if self.secure else "http"
            self.base_url = f"{scheme}://{raw_endpoint.lstrip('/')}"

        missing = self._missing_key_vars()
        if missing and settings.is_deployed:
            raise ConfigurationError(
                f"Silo keys are not set in the '{settings.environment}' environment: "
                f"{', '.join(missing)}. They have no default."
            )

    def _missing_key_vars(self) -> list[str]:
        pairs = ((ACCESS_KEY_VAR, self.access_key), (SECRET_KEY_VAR, self.secret_key))
        return [var for var, value in pairs if not value]

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

    def _object_url(self, bucket: str, object_key: str) -> str:
        return f"{self.base_url}/{bucket}/{object_key}"

    def _request(
        self,
        method: str,
        bucket: str,
        object_key: str,
        *,
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Sign and send one request to Silo. Missing keys and transport failures raise
        AssetStorageError."""
        missing = self._missing_key_vars()
        if missing:
            raise AssetStorageError(
                f"Silo {method} for '{bucket}/{object_key}' was not sent: "
                f"{', '.join(missing)} not set.",
                bucket=bucket,
                object_key=object_key,
            )
        url = self._object_url(bucket, object_key)
        signed = sigv4_headers(
            method,
            url,
            headers=headers or {},
            body=content,
            access_key=self.access_key or "",
            secret_key=self.secret_key or "",
            region=self.region,
        )
        try:
            with httpx.Client(timeout=SILO_TIMEOUT_SECONDS, transport=self._transport) as client:
                return client.request(method, url, content=content or None, headers=signed)
        except httpx.HTTPError as exc:
            raise AssetStorageError(
                f"Silo {method} failed for '{bucket}/{object_key}': {exc}",
                bucket=bucket,
                object_key=object_key,
            ) from exc

    def upload_asset(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str,
        owner_id: str,
        asset_id: str | None = None,
    ) -> dict[str, Any]:
        """Validate media, PUT the bytes to Silo, and return the stored object metadata.

        Raises AssetValidationError for rejected payloads and AssetStorageError when
        Silo does not confirm the write. Nothing is recorded on failure.
        """
        self.validate_asset(data=data, content_type=content_type)

        resp = self._request(
            "PUT",
            bucket,
            object_key,
            content=data,
            headers={"Content-Type": content_type},
        )
        if resp.status_code not in (200, 201, 204):
            raise AssetStorageError(
                f"Silo PUT for '{bucket}/{object_key}' returned status {resp.status_code}.",
                bucket=bucket,
                object_key=object_key,
            )

        return {
            "asset_id": asset_id or str(uuid4()),
            "bucket": bucket,
            "object_key": object_key,
            "content_type": content_type,
            "byte_size": len(data),
            "owner_id": owner_id,
            "created_at": datetime.now(UTC).isoformat(),
        }

    def get_asset(self, bucket: str, object_key: str) -> tuple[bytes, str]:
        """Retrieve asset binary content and content-type from Silo."""
        resp = self._request("GET", bucket, object_key)
        if resp.status_code == 404:
            raise AssetNotFoundError(f"{bucket}/{object_key}")
        if resp.status_code != 200:
            raise AssetStorageError(
                f"Silo GET for '{bucket}/{object_key}' returned status {resp.status_code}.",
                bucket=bucket,
                object_key=object_key,
            )
        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        return resp.content, content_type

    def check_bucket(self, bucket: str | None = None) -> None:
        """Send one signed HEAD for the bucket. Raise AssetStorageError unless Silo answers 200.

        The readiness probe uses it. A missing bucket (404) or a refused signature (403)
        is a failure, because no upload can succeed then.
        """
        name = bucket or self.default_bucket
        resp = self._request("HEAD", name, "")
        if resp.status_code != 200:
            raise AssetStorageError(
                f"Silo HEAD for bucket '{name}' returned status {resp.status_code}.",
                bucket=name,
                object_key="",
            )

    def delete_asset(self, bucket: str, object_key: str) -> None:
        """Delete an object from Silo. Missing objects raise AssetNotFoundError."""
        resp = self._request("DELETE", bucket, object_key)
        if resp.status_code == 404:
            raise AssetNotFoundError(f"{bucket}/{object_key}")
        if resp.status_code not in (200, 204):
            raise AssetStorageError(
                f"Silo DELETE for '{bucket}/{object_key}' returned status {resp.status_code}.",
                bucket=bucket,
                object_key=object_key,
            )


def log_storage_failure(log: logging.Logger, action: str, exc: AssetStorageError) -> None:
    """Log a Silo failure at error level with the bucket and the object key.

    Call it where a route maps the failure to HTTP 503 (ADR-0015). The record holds the
    error message only. It never holds the object bytes or the Silo credentials.
    """
    log.error(
        "Silo %s failed: bucket=%s object_key=%s error=%s",
        action,
        exc.bucket,
        exc.object_key,
        exc.message,
    )


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
