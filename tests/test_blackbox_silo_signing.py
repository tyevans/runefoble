"""Blackbox suite for TASK-0926: the Silo client signs requests and needs its keys.

The Silo HTTP boundary is the FakeSilo transport. Like the real Silo, it refuses an
unsigned request with 403. The settings tests build the client from the environment, as a
service does at start-up.
"""

from __future__ import annotations

import httpx
import pytest
from runefoble_platform.errors import ConfigurationError
from runefoble_platform.storage import AssetStorageError, SiloStorageService

from tests.helpers.silo_fixtures import (
    PNG_SAMPLE_BYTES,
    SILO_TEST_ENDPOINT,
    SILO_UNSIGNED_STATUS,
    FakeSilo,
)

BUCKET = "runefoble-assets"
KEY_VARS = ("RUNEFOBLE_SILO_ACCESS_KEY", "RUNEFOBLE_SILO_SECRET_KEY")


def test_the_silo_double_refuses_an_unsigned_request(silo_double: FakeSilo) -> None:
    with httpx.Client(transport=silo_double.transport()) as client:
        response = client.put(f"{SILO_TEST_ENDPOINT}/{BUCKET}/unsigned.png", content=b"x")

    assert response.status_code == SILO_UNSIGNED_STATUS
    assert silo_double.objects == {}


def test_the_platform_client_sends_signed_requests(silo_double: FakeSilo) -> None:
    from runefoble_platform.storage import get_storage_service

    storage = get_storage_service()
    storage.upload_asset(BUCKET, "signed.png", PNG_SAMPLE_BYTES, "image/png", owner_id="u-1")

    assert storage.get_asset(BUCKET, "signed.png") == (PNG_SAMPLE_BYTES, "image/png")


@pytest.mark.parametrize("missing", KEY_VARS)
def test_a_deployed_client_without_silo_keys_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.setenv("RUNEFOBLE_ENVIRONMENT", "production")
    for var in KEY_VARS:
        monkeypatch.setenv(var, "set-by-the-operator")
    monkeypatch.delenv(missing)

    with pytest.raises(ConfigurationError, match=missing):
        SiloStorageService(endpoint=SILO_TEST_ENDPOINT)


def test_a_deployed_client_with_silo_keys_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_ENVIRONMENT", "production")
    for var in KEY_VARS:
        monkeypatch.setenv(var, "set-by-the-operator")

    SiloStorageService(endpoint=SILO_TEST_ENDPOINT)


def test_a_development_client_without_keys_fails_each_request_visibly(
    monkeypatch: pytest.MonkeyPatch, silo_double: FakeSilo
) -> None:
    monkeypatch.setenv("RUNEFOBLE_ENVIRONMENT", "development")
    for var in KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    storage = SiloStorageService(endpoint=SILO_TEST_ENDPOINT, transport=silo_double.transport())

    with pytest.raises(AssetStorageError, match="RUNEFOBLE_SILO_ACCESS_KEY") as caught:
        storage.upload_asset(BUCKET, "no-keys.png", PNG_SAMPLE_BYTES, "image/png", "u-1")

    assert caught.value.object_key == "no-keys.png"
    assert silo_double.objects == {}
