"""Blackbox tests (TASK-0818): every service reads the one SpiceDB client from the lib factory.

A test swaps the client through the public seam `runefoble_auth.factory.set_spicedb_client`.
The swapped client must reach each service's permission-checked route over HTTP. A service
that keeps its own client would answer from the default mock and fail these tests.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from character_sheet.main import app as character_sheet_app
from fastapi.testclient import TestClient
from game_session.main import app as game_session_app
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.factory import get_spicedb_client, set_spicedb_client
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.module_state import restored_seam
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

OUTAGE_BODY = {"error": "authorization_unavailable"}


class _OutageSpiceDB(MockSpiceDBClient):
    """The SpiceDB process boundary, unreachable. A permission check raises the typed error."""

    async def check_permission(self, *_args: Any, **_kwargs: Any) -> bool:
        raise AuthzUnavailableError("SpiceDB did not answer")


def _bearer() -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint('single-client-user')}"}


PROBES = [
    pytest.param(
        game_session_app,
        "POST",
        "/api/v1/sessions/create",
        {"campaign_id": str(uuid4())},
        id="game_session",
    ),
    pytest.param(
        character_sheet_app,
        "GET",
        f"/api/v1/characters/{uuid4()}",
        None,
        id="character_sheet",
    ),
]


@pytest.mark.parametrize(("app", "method", "path", "json_body"), PROBES)
def test_factory_client_answers_every_service_route(
    app: Any, method: str, path: str, json_body: dict[str, Any] | None
) -> None:
    """The client set on the lib seam decides the answer of each service's permission check."""
    with restored_seam(get_spicedb_client, set_spicedb_client, _OutageSpiceDB(), replace=True):
        client = TestClient(app, raise_server_exceptions=False)
        res = client.request(method, path, json=json_body, headers=_bearer())

    assert res.status_code == 503, res.text
    assert res.json() == OUTAGE_BODY


def test_factory_seam_restores_the_previous_client() -> None:
    """Leaving the seam puts back the client that held the factory before the swap."""
    before = get_spicedb_client()
    with restored_seam(get_spicedb_client, set_spicedb_client, _OutageSpiceDB(), replace=True):
        assert isinstance(get_spicedb_client(), _OutageSpiceDB)

    assert get_spicedb_client() is before
