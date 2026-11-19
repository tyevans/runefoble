"""The identity sync service takes its SpiceDB client and Zitadel verifier from the caller."""

from __future__ import annotations

import pytest
from runefoble_auth.mock.client import MockSpiceDBClient
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_auth.zitadel import ZitadelAuthService


def _verifier() -> ZitadelAuthService:
    return ZitadelAuthService(
        issuer="http://zitadel.test", audience="runefoble-api", internal_url=None
    )


def test_constructing_without_adapters_raises_type_error() -> None:
    with pytest.raises(TypeError):
        ZitadelSpiceDBSyncService()  # type: ignore[call-arg]


def test_constructing_without_zitadel_verifier_raises_type_error() -> None:
    with pytest.raises(TypeError):
        ZitadelSpiceDBSyncService(MockSpiceDBClient())  # type: ignore[call-arg]


def test_constructing_without_spicedb_client_raises_type_error() -> None:
    with pytest.raises(TypeError):
        ZitadelSpiceDBSyncService(zitadel_auth=_verifier())  # type: ignore[call-arg]


def test_constructor_accepts_both_adapters() -> None:
    spicedb = MockSpiceDBClient()
    verifier = _verifier()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb, zitadel_auth=verifier)
    assert service.spicedb is spicedb
    assert service.zitadel is verifier
