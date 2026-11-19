"""Shared subject permission check: one denial type, and failures never look like denials (TASK-0817).

The fake below stands in for the SpiceDB process boundary. It answers `check_permission`
with a fixed result or raises a typed authz error, as the live client does.

Governed by ADR-0001 (fail closed) and TASK-0813 (503 for authz failures).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import (
    PermissionDenied,
    check_subject,
    require_permission,
    require_subject,
)


class FakeSpiceDB:
    """Records each check and returns the configured answer, or raises the configured error."""

    def __init__(self, answer: bool = True, error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.calls: list[tuple[str, str, str, str, str]] = []

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        self.calls.append((resource_type, resource_id, permission, subject_type, subject_id))
        if self.error is not None:
            raise self.error
        return self.answer


@pytest.mark.asyncio
async def test_check_subject_asks_spicedb_about_the_user_subject():
    spicedb = FakeSpiceDB(answer=True)

    assert await check_subject(spicedb, "campaign", 42, "view", "alice") is True

    assert spicedb.calls == [("campaign", "42", "view", "user", "alice")]


@pytest.mark.asyncio
async def test_require_subject_allows_a_holder_without_raising():
    spicedb = FakeSpiceDB(answer=True)

    await require_subject(spicedb, "shared_world", "w1", "manage", "alice")

    assert spicedb.calls == [("shared_world", "w1", "manage", "user", "alice")]


@pytest.mark.asyncio
async def test_require_subject_denies_with_403_and_the_standard_detail():
    spicedb = FakeSpiceDB(answer=False)

    with pytest.raises(PermissionDenied) as exc:
        await require_subject(spicedb, "shared_world", "w1", "manage", "mallory")

    assert exc.value.status_code == 403
    assert exc.value.detail == (
        "Permission denied: subject 'mallory' lacks 'manage' on shared_world:w1"
    )


@pytest.mark.asyncio
async def test_require_subject_keeps_a_route_specific_denial_wording():
    spicedb = FakeSpiceDB(answer=False)

    with pytest.raises(PermissionDenied) as exc:
        await require_subject(
            spicedb, "stronghold", "c1", "upgrade", "mallory", detail="Campaign view required"
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Campaign view required"


@pytest.mark.asyncio
async def test_authz_failure_is_not_reported_as_a_denial():
    spicedb = FakeSpiceDB(error=AuthzUnavailableError("SpiceDB UNAVAILABLE"))

    with pytest.raises(AuthzUnavailableError):
        await require_subject(spicedb, "campaign", "c1", "view", "alice")

    with pytest.raises(AuthzUnavailableError):
        await check_subject(spicedb, "campaign", "c1", "view", "alice")


# --- require_permission: the route dependency factory (TASK-0817) ---------------------------


def _principal_as(user_id: str | None):
    async def _principal():
        return SimpleNamespace(user_id=user_id)

    return _principal


def _app(spicedb: FakeSpiceDB, *, principal, **options) -> tuple[FastAPI, dict]:
    app = FastAPI()
    install_authz_error_handlers(app)
    app.dependency_overrides[get_spicedb_client] = lambda: spicedb
    seen: dict = {}
    guard = require_permission("campaign", "view", "campaign_id", principal=principal, **options)

    @app.get("/campaigns/{campaign_id}", dependencies=[Depends(guard)])
    async def read_campaign(campaign_id: str):
        seen["campaign_id"] = campaign_id
        return {"ok": True}

    return app, seen


def test_require_permission_lets_a_holder_reach_the_handler():
    spicedb = FakeSpiceDB(answer=True)
    app, seen = _app(spicedb, principal=_principal_as("alice"))

    response = TestClient(app).get("/campaigns/c1")

    assert response.status_code == 200
    assert seen["campaign_id"] == "c1"
    assert spicedb.calls == [("campaign", "c1", "view", "user", "alice")]


def test_require_permission_denies_a_stranger_with_403_before_the_handler_runs():
    spicedb = FakeSpiceDB(answer=False)
    app, seen = _app(spicedb, principal=_principal_as("mallory"))

    response = TestClient(app).get("/campaigns/c1")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied: subject 'mallory' lacks 'view' on campaign:c1"
    }
    assert "campaign_id" not in seen


def test_require_permission_reports_spicedb_failure_as_503_not_403():
    spicedb = FakeSpiceDB(error=AuthzUnavailableError("SpiceDB UNAVAILABLE"))
    app, seen = _app(spicedb, principal=_principal_as("alice"))

    response = TestClient(app).get("/campaigns/c1")

    assert response.status_code == 503
    assert response.json() == {"error": "authorization_unavailable"}
    assert "campaign_id" not in seen


def test_require_permission_coerces_the_path_id_to_the_declared_type():
    spicedb = FakeSpiceDB(answer=True)
    character_id = uuid4()
    app = FastAPI()
    install_authz_error_handlers(app)
    app.dependency_overrides[get_spicedb_client] = lambda: spicedb
    guard = require_permission(
        "character", "edit", "character_id", principal=_principal_as("alice"), id_type=UUID
    )

    @app.get("/characters/{character_id}", dependencies=[Depends(guard)])
    async def read_character(character_id: UUID):
        return {"id": str(character_id)}

    client = TestClient(app)

    assert client.get(f"/characters/{character_id}").status_code == 200
    assert spicedb.calls == [("character", str(character_id), "edit", "user", "alice")]
    assert client.get("/characters/not-a-uuid").status_code == 422


def test_require_permission_service_call_passes_without_a_user_when_allowed():
    spicedb = FakeSpiceDB(answer=False)
    app, seen = _app(spicedb, principal=_principal_as(None), allow_service=True)

    response = TestClient(app).get("/campaigns/c1")

    assert response.status_code == 200
    assert seen["campaign_id"] == "c1"
    assert spicedb.calls == []


def test_require_permission_service_call_without_a_user_is_denied_when_not_allowed():
    spicedb = FakeSpiceDB(answer=True)
    app, seen = _app(spicedb, principal=_principal_as(None))

    response = TestClient(app).get("/campaigns/c1")

    assert response.status_code == 403
    assert "campaign_id" not in seen
    assert spicedb.calls == []


def test_require_permission_uses_the_route_denial_body_when_given():
    spicedb = FakeSpiceDB(answer=False)

    def denial(resource_type: str, resource_id: str, permission: str, user_id: str):
        return HTTPException(
            status_code=403,
            detail={"error": "permission_denied", "resource": f"{resource_type}:{resource_id}"},
        )

    app, _ = _app(spicedb, principal=_principal_as("mallory"), denial=denial)

    response = TestClient(app).get("/campaigns/c1")

    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "permission_denied", "resource": "campaign:c1"}}
