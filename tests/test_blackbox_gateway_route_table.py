"""Blackbox frontdoor tests for the gateway route table and the owner client (TASK-0822).

Governing ADRs: ADR-0015 (b: the gateway is thin, returns no substitute value; c: the caller's
bearer is forwarded), ADR-0001 (the owner keeps the object checks).

Part 1 drives every pure pass-through row of the proxy tables through the public gateway routes.
One loopback stub stands in for each owner. It echoes the method, path, and query it receives,
and it answers with a status that the test selects. The stub does not reach into gateway state.

Part 2 covers G-12: a character reply carries the campaign title, and an owner reply that is not
JSON returns 502.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from gateway_api.routers import (
    assets_proxy,
    audience,
    boards_proxy,
    campaigns_proxy,
    caravan_proxy,
    compendium_proxy,
    downtime_proxy,
    forge_proxy,
    settlements_proxy,
    soundscape,
    voice_proxy,
    watcher_speech_proxy,
)
from gateway_api.routers.auth import profile
from runefoble_platform.service_client import OWNER_URL_FIELDS

from tests.helpers.live_services import closed_port_url, serve

ROUTE_MODULES = (
    assets_proxy,
    audience,
    boards_proxy,
    campaigns_proxy,
    caravan_proxy,
    compendium_proxy,
    downtime_proxy,
    forge_proxy,
    profile,
    settlements_proxy,
    soundscape,
    voice_proxy,
    watcher_speech_proxy,
)
# Body models need a valid body, which the owner contract defines. Those rows are covered by the
# downtime contract tests. This table checks the forwarding of every other row.
TABLE_ROWS = [
    pytest.param(row, id=f"{row.method} {row.public_path}")
    for module in ROUTE_MODULES
    for row in module.ROUTES
    if row.body_model is None
]
VALUE = "probe-id"
OWNER_STATUS = {"code": 200}

stub_app = FastAPI()


@stub_app.api_route("/{owner_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def owner_stub(owner_path: str, request: Request) -> Response:
    """Echo what the owner received, or answer with the status that the test selected."""
    body = await request.body()
    if OWNER_STATUS["code"] == 418:
        return JSONResponse({"detail": "owner refused"}, status_code=418)
    if OWNER_STATUS["code"] == 500:
        return JSONResponse({"detail": "owner broke"}, status_code=500)
    return JSONResponse(
        {
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "body": body.decode("utf-8", errors="replace"),
        }
    )


@pytest.fixture(scope="module")
def owner_stub_url() -> Iterator[str]:
    with serve(stub_app) as url:
        yield url


def _owner_env(service: str) -> str:
    """The environment variable of an owner base URL. The Watcher keeps its short name."""
    if service == "the_watcher":
        return "RUNEFOBLE_WATCHER_URL"
    return "RUNEFOBLE_" + OWNER_URL_FIELDS[service].upper()


@contextmanager
def _gateway(monkeypatch, stub_url: str, *, down: str | None = None) -> Iterator[TestClient]:
    """Enter the gateway lifespan with every owner served by the stub, except `down`."""
    for service in OWNER_URL_FIELDS:
        monkeypatch.setenv(_owner_env(service), stub_url)
    if down is not None:
        monkeypatch.setenv(_owner_env(down), closed_port_url())
    with TestClient(gateway_app) as client:
        yield client


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _concrete(row: Any) -> tuple[str, str]:
    """Return the public URL and the expected owner path of one row with a sample value."""
    public = re.sub(r"\{\w+\}", VALUE, row.public_path)
    values = dict.fromkeys(re.findall(r"\{(\w+)\}", row.public_path), VALUE)
    return public, row.owner_path(values)


def _send(client: TestClient, row: Any, headers: dict[str, str], query: str = "") -> Any:
    url = _concrete(row)[0] + (f"?{query}" if query else "")
    kwargs: dict[str, Any] = {"headers": headers}
    if row.body == "json":
        kwargs["json"] = {"probe": 1}
    elif row.body == "raw":
        kwargs["content"] = b"raw-bytes"
        kwargs["headers"] = {**headers, "Content-Type": "application/octet-stream"}
    return client.request(row.method, url, **kwargs)


@pytest.mark.parametrize("row", TABLE_ROWS)
def test_table_route_forwards_method_path_query_and_payload(
    row, owner_stub_url, monkeypatch, trusted_ws_issuer
):
    """The owner receives the owner path, the method, and the payload. The status follows the row."""
    OWNER_STATUS["code"] = 200
    with _gateway(monkeypatch, owner_stub_url) as client:
        res = _send(client, row, _auth(trusted_ws_issuer, "user_table"), query="probe=1")

    # A bytes reply relays the owner's status. A JSON reply takes the status the row declares.
    expected = 200 if row.reply == "bytes" else (row.status_code or 200)
    assert res.status_code == expected, res.text
    echo = res.json()
    assert echo["method"] == row.method
    assert echo["path"] == _concrete(row)[1]
    if row.query_all:
        assert echo["query"] == "probe=1"
    if row.query_defaults:
        assert "reason=removed" in echo["query"]
    if row.body == "json":
        assert '"probe"' in echo["body"]
    if row.body == "raw":
        assert echo["body"] == "raw-bytes"


@pytest.mark.parametrize("row", TABLE_ROWS)
def test_table_route_relays_an_owner_client_error_unchanged(
    row, owner_stub_url, monkeypatch, trusted_ws_issuer
):
    """An owner 4xx answer reaches the caller with its status and body."""
    OWNER_STATUS["code"] = 418
    try:
        with _gateway(monkeypatch, owner_stub_url) as client:
            res = _send(client, row, _auth(trusted_ws_issuer, "user_table"))
    finally:
        OWNER_STATUS["code"] = 200

    assert res.status_code == 418
    assert res.json() == {"detail": "owner refused"}


@pytest.mark.parametrize("row", TABLE_ROWS)
def test_table_route_maps_an_owner_failure_to_502(
    row, owner_stub_url, monkeypatch, trusted_ws_issuer
):
    """An owner 5xx answer returns 502 with the upstream name and no owner detail."""
    OWNER_STATUS["code"] = 500
    try:
        with _gateway(monkeypatch, owner_stub_url) as client:
            res = _send(client, row, _auth(trusted_ws_issuer, "user_table"))
    finally:
        OWNER_STATUS["code"] = 200

    assert res.status_code == 502
    assert res.json() == {"detail": "Upstream service is unavailable", "upstream": row.service}


@pytest.mark.parametrize("row", TABLE_ROWS)
def test_table_route_maps_an_unreachable_owner_to_503(
    row, owner_stub_url, monkeypatch, trusted_ws_issuer
):
    """An owner that cannot be reached returns 503 with the upstream name."""
    OWNER_STATUS["code"] = 200
    with _gateway(monkeypatch, owner_stub_url, down=row.service) as client:
        res = _send(client, row, _auth(trusted_ws_issuer, "user_table"))

    assert res.status_code == 503
    assert res.json() == {"detail": "Upstream service is unavailable", "upstream": row.service}


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/campaigns/%2E%2E",
        "/api/v1/boards/%2E%2E",
        "/api/v1/shared-worlds/%2E%2E/caravans/contracts",
    ],
)
def test_a_dot_segment_returns_404_without_an_owner_call(
    url, owner_stub_url, monkeypatch, trusted_ws_issuer
):
    """A path value the owner path cannot encode is a missing resource. The owner stub answers 200
    to any path, so a 404 shows that the gateway refused the request before it reached the owner."""
    OWNER_STATUS["code"] = 200
    with _gateway(monkeypatch, owner_stub_url) as client:
        res = client.get(url, headers=_auth(trusted_ws_issuer, "user_table"))

    assert res.status_code == 404, res.text


# G-12: the character reply carries the campaign title, and a non-JSON owner reply returns 502.


def _create_member_campaign_character(client: TestClient, issuers: dict[str, dict[str, str]]):
    """Set up a campaign with a member who owns a character assigned to it. Use public routes only."""
    campaign_id = client.post(
        "/api/v1/campaigns",
        json={"title": "Curse of Strahd", "setting": "Barovia"},
        headers=issuers["dm"],
    ).json()["id"]
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
        headers=issuers["dm"],
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=issuers["member"],
    )
    assert joined.status_code == 200, joined.text
    char_id = client.post(
        "/api/v1/characters",
        json={"name": "Alice Barovian", "characterClass": "Cleric", "maxHp": 12},
        headers=issuers["member"],
    ).json()["id"]
    assigned = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": campaign_id},
        headers=issuers["member"],
    )
    assert assigned.status_code == 200, assigned.text
    return char_id


def test_mutation_reply_carries_the_campaign_title_for_a_member(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A health change returns the same campaign title that a read returns (G-12)."""
    issuers = {
        "dm": _auth(trusted_ws_issuer, "dm_merlin"),
        "member": _auth(trusted_ws_issuer, "user_grognak"),
    }
    with TestClient(gateway_app) as client:
        char_id = _create_member_campaign_character(client, issuers)
        changed = client.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -2, "source": "damage"},
            headers=issuers["member"],
        )
        read = client.get(f"/api/v1/characters/{char_id}", headers=issuers["member"])

    assert changed.status_code == 200, changed.text
    assert read.status_code == 200, read.text
    assert changed.json()["campaignTitle"] == "Curse of Strahd"
    assert changed.json()["campaignTitle"] == read.json()["campaignTitle"]


def test_guardrails_reply_that_is_not_json_maps_to_502(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream, monkeypatch
):
    """An owner that answers 2xx with a body that is not JSON returns 502, never a 500 (G-12)."""
    headers = _auth(trusted_ws_issuer, "user_guardrails")
    with TestClient(gateway_app) as client:
        char_id = client.post(
            "/api/v1/characters",
            json={"name": "Warden", "characterClass": "Fighter", "maxHp": 10},
            headers=headers,
        ).json()["id"]

    text_app = FastAPI()

    @text_app.put("/api/v1/characters/{character_id}/guardrails")
    def _not_json(character_id: str) -> PlainTextResponse:
        return PlainTextResponse("stored, no json here", status_code=200)

    with serve(text_app) as text_url:
        monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", text_url)
        with TestClient(gateway_app) as client:
            res = client.put(
                f"/api/v1/characters/{char_id}/guardrails",
                json={"risk_threshold": "cautious"},
                headers=headers,
            )

    assert res.status_code == 502
    assert res.json() == {"detail": "Upstream service returned an invalid response"}
