"""The shared SpiceDB client factory (TASK-0541)."""

from __future__ import annotations

import pytest
from runefoble_auth import factory
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.errors import ConfigurationError

KEY_VAR = "RUNEFOBLE_SPICEDB_PRESHARED_KEY"


@pytest.fixture(autouse=True)
def _fresh_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(factory, "_client", None)


def test_factory_builds_client_from_the_preshared_key_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(KEY_VAR, "key-from-setting")
    monkeypatch.setenv("RUNEFOBLE_SPICEDB_ENDPOINT", "spicedb.test:50051")

    client = get_spicedb_client()

    assert isinstance(client, SpiceDBClient)
    assert client.token == "key-from-setting"
    assert client.endpoint == "spicedb.test:50051"


def test_factory_returns_one_cached_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEY_VAR, "key-from-setting")

    assert get_spicedb_client() is get_spicedb_client()


def test_factory_raises_configuration_error_when_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(KEY_VAR, raising=False)

    with pytest.raises(ConfigurationError, match=KEY_VAR):
        get_spicedb_client()
