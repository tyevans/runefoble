"""The shared SpiceDB client factory (TASK-0541)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from runefoble_auth.factory import get_spicedb_client, set_spicedb_client
from runefoble_auth.mock.client import MockSpiceDBClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.errors import ConfigurationError

KEY_VAR = "RUNEFOBLE_SPICEDB_PRESHARED_KEY"


@pytest.fixture(autouse=True)
def _fresh_factory() -> Iterator[None]:
    set_spicedb_client(None)
    yield
    set_spicedb_client(None)


def test_factory_builds_client_from_the_preshared_key_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(KEY_VAR, "key-from-setting")
    monkeypatch.setenv("RUNEFOBLE_SPICEDB_ENDPOINT", "spicedb.test:50051")

    client = get_spicedb_client()

    assert isinstance(client, SpiceDBClient)
    assert client.token == "key-from-setting"
    assert client.endpoint == "spicedb.test:50051"


def test_factory_reads_the_legacy_endpoint_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPICEDB_ENDPOINT stays a valid name for the endpoint (TASK-0720)."""
    monkeypatch.setenv(KEY_VAR, "key-from-setting")
    monkeypatch.delenv("RUNEFOBLE_SPICEDB_ENDPOINT", raising=False)
    monkeypatch.setenv("SPICEDB_ENDPOINT", "legacy.test:50051")

    assert get_spicedb_client().endpoint == "legacy.test:50051"


def test_factory_raises_configuration_error_when_key_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(KEY_VAR, "")

    with pytest.raises(ConfigurationError, match=KEY_VAR):
        get_spicedb_client()


def test_factory_returns_one_cached_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEY_VAR, "key-from-setting")

    assert get_spicedb_client() is get_spicedb_client()


def test_factory_raises_configuration_error_when_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(KEY_VAR, raising=False)

    with pytest.raises(ConfigurationError, match=KEY_VAR):
        get_spicedb_client()


def test_set_spicedb_client_replaces_the_shared_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEY_VAR, "key-from-setting")
    replacement = MockSpiceDBClient()

    set_spicedb_client(replacement)

    assert get_spicedb_client() is replacement


def test_set_spicedb_client_none_forces_a_fresh_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEY_VAR, "key-from-setting")
    set_spicedb_client(MockSpiceDBClient())

    set_spicedb_client(None)

    assert isinstance(get_spicedb_client(), SpiceDBClient)
