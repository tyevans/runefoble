"""Blackbox suite for TASK-0926: the Silo client signs its requests against real MinIO.

The pinned Silo image of the chart refuses unsigned S3 requests. These tests run that image
in Docker and use `SiloStorageService` through its public methods only. They skip when
Docker is not available.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from runefoble_platform.storage import AssetNotFoundError, AssetStorageError, SiloStorageService

from tests.helpers.minio_container import MinioServer, minio_container
from tests.helpers.ports import free_port
from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES

BUCKET = "runefoble-assets"


@pytest.fixture(scope="module")
def minio() -> Iterator[MinioServer]:
    with minio_container(free_port(), BUCKET) as server:
        yield server


def _client(server: MinioServer, *, secret_key: str | None = None) -> SiloStorageService:
    return SiloStorageService(
        endpoint=server.endpoint,
        access_key=server.access_key,
        secret_key=secret_key or server.secret_key,
        bucket_assets=server.bucket,
        secure=False,
    )


def test_signed_upload_read_and_delete_round_trip(minio: MinioServer) -> None:
    storage = _client(minio)
    key = "maps/round-trip.png"

    stored = storage.upload_asset(BUCKET, key, PNG_SAMPLE_BYTES, "image/png", owner_id="u-1")
    data, content_type = storage.get_asset(BUCKET, key)
    storage.delete_asset(BUCKET, key)

    assert stored["byte_size"] == len(PNG_SAMPLE_BYTES)
    assert data == PNG_SAMPLE_BYTES
    assert content_type == "image/png"
    with pytest.raises(AssetNotFoundError):
        storage.get_asset(BUCKET, key)


def test_read_of_a_missing_object_is_not_found(minio: MinioServer) -> None:
    with pytest.raises(AssetNotFoundError):
        _client(minio).get_asset(BUCKET, "maps/never-written.png")


def test_wrong_secret_key_raises_a_typed_storage_error(minio: MinioServer) -> None:
    storage = _client(minio, secret_key="not-the-silo-secret")

    with pytest.raises(AssetStorageError) as caught:
        storage.upload_asset(BUCKET, "maps/refused.png", PNG_SAMPLE_BYTES, "image/png", "u-1")

    assert caught.value.bucket == BUCKET
    assert caught.value.object_key == "maps/refused.png"
    assert "403" in caught.value.message
    assert "not-the-silo-secret" not in caught.value.message
