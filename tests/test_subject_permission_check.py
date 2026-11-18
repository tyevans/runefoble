"""Shared subject permission check: one denial type, and failures never look like denials (TASK-0817).

The fake below stands in for the SpiceDB process boundary. It answers `check_permission`
with a fixed result or raises a typed authz error, as the live client does.

Governed by ADR-0001 (fail closed) and TASK-0813 (503 for authz failures).
"""

from __future__ import annotations

import pytest
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.permissions import PermissionDenied, check_subject, require_subject


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
