"""Blackbox frontdoor tests (TASK-0813): every SpiceDB-backed service maps one outage to one 503.

A SpiceDB outage is not a denial. Each service answers the same body on a permission-checked
route: `{"error": "authorization_unavailable"}` with HTTP 503. A schema defect (a name missing
from runefoble.zed) is a server fault: HTTP 500 with an error id, logged, never a 503.

The only stub is the SpiceDB process boundary: `check_permission` raises the typed error. Every
request goes through a public HTTP route. No service keeps its own copy of the mapping.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization (fail closed)
- ADR-0015: Audit remediation decisions (SVC-01)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
from asset_forge.main import app as asset_forge_app
from character_sheet.main import app as character_sheet_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from game_session.main import app as game_session_app
from runefoble_auth.errors import AuthzSchemaError, AuthzUnavailableError
from runefoble_auth.mock import MockSpiceDBClient
from the_watcher.main import app as the_watcher_app

from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

USER = "outage-user"
OUTAGE_BODY = {"error": "authorization_unavailable"}


@dataclass(frozen=True)
class Probe:
    """One permission-checked route of one service, with a body that passes validation.

    A service that needs a live store or engine before its permission check names a fixture in
    `under_test`. That fixture yields `(client, spicedb)`. Other services set `app` only.
    """

    service: str
    method: str
    path: str
    app: FastAPI | None = None
    under_test: str | None = None
    json: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=lambda: bearer(USER))


PROBES = [
    Probe(
        "game_session",
        "POST",
        f"/api/v1/sessions/{uuid4()}/start",
        app=game_session_app,
    ),
    Probe(
        "the_watcher",
        "POST",
        "/api/v1/watcher/veto",
        app=the_watcher_app,
        json={
            "action_id": "act-outage",
            "session_id": str(uuid4()),
            "campaign_id": str(uuid4()),
            "reason": "outage",
        },
    ),
    Probe("character_sheet", "GET", f"/api/v1/characters/{uuid4()}", app=character_sheet_app),
    Probe(
        "campaign_lore",
        "POST",
        "/api/v1/lore/search",
        under_test="lore_under_test",
        json={"campaign_id": str(uuid4()), "query": "the sunken crypt"},
    ),
    Probe(
        "asset_forge",
        "POST",
        "/api/v1/forge/token",
        app=asset_forge_app,
        json={
            "token_name": "Ghoul",
            "prompt": "Gaunt ghoul with rusted claws",
            "campaign_id": str(uuid4()),
        },
    ),
    Probe(
        "campaign_analytics",
        "GET",
        f"/api/v1/analytics/campaigns/{uuid4()}/heatmap",
        under_test="analytics_under_test",
    ),
]


@pytest.fixture
def lore_under_test(
    lore_backends: dict[str, str | int], default_spicedb_client: MockSpiceDBClient | None
) -> Iterator[tuple[TestClient, MockSpiceDBClient]]:
    """Campaign Lore with its lifespan, on the PostgreSQL and embedding stand-ins."""
    from campaign_lore.main import app as campaign_lore_app

    assert default_spicedb_client is not None
    with TestClient(campaign_lore_app, raise_server_exceptions=False) as client:
        yield client, default_spicedb_client


@pytest.fixture
def analytics_under_test(
    analytics_service: Any,
) -> Iterator[tuple[TestClient, MockSpiceDBClient]]:
    """Campaign Analytics with its lifespan, on the PostgreSQL container and the Redis double."""
    with analytics_service.start() as client:
        yield client, analytics_service.spicedb


@contextmanager
def _service_under_test(
    probe: Probe, request: pytest.FixtureRequest
) -> Iterator[tuple[TestClient, MockSpiceDBClient]]:
    """Yield a client for the probe and the SpiceDB double that the service checks against."""
    if probe.under_test is not None:
        yield request.getfixturevalue(probe.under_test)
        return
    # No lifespan: the outage is the only fault under test. Errors become responses, not raises.
    spicedb = request.getfixturevalue("default_spicedb_client")
    yield TestClient(probe.app, raise_server_exceptions=False), spicedb


def _failing_check(error: Exception) -> Callable[..., Any]:
    async def check_permission(*_args: Any, **_kwargs: Any) -> bool:
        raise error

    return check_permission


@pytest.mark.parametrize("probe", PROBES, ids=lambda p: p.service)
def test_spicedb_outage_answers_one_503_body(
    probe: Probe, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With SpiceDB unreachable, the route answers 503 with the one body. It is not a denial."""
    with _service_under_test(probe, request) as (client, spicedb):
        monkeypatch.setattr(
            spicedb,
            "check_permission",
            _failing_check(AuthzUnavailableError("SpiceDB did not answer")),
        )
        res = client.request(probe.method, probe.path, json=probe.json, headers=probe.headers)

    assert res.status_code == 503, res.text
    assert res.json() == OUTAGE_BODY


@pytest.mark.parametrize("probe", PROBES, ids=lambda p: p.service)
def test_spicedb_schema_defect_answers_500_with_error_id(
    probe: Probe, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A permission name missing from the schema is a 500 with an error id, never a 503."""
    with _service_under_test(probe, request) as (client, spicedb):
        monkeypatch.setattr(
            spicedb,
            "check_permission",
            _failing_check(AuthzSchemaError("permission not in schema")),
        )
        res = client.request(probe.method, probe.path, json=probe.json, headers=probe.headers)

    assert res.status_code == 500, res.text
    body = res.json()
    assert body["error"] == "authorization_schema_error"
    assert body["error_id"]
