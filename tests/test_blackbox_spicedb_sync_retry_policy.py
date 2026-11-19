"""Retry policy of the SpiceDB identity sync service (TASK-0853).

Only `AuthzUnavailableError` (a transport failure) is retried. A schema rejection, a failed
write, and any other exception are permanent and propagate on the first attempt.

The counting double stands in for the SpiceDB client at the process boundary. The tests
call the public sync methods and assert the observable outcome: the number of attempts and
the typed error that the caller receives.
"""

from __future__ import annotations

from typing import Any

import pytest
from runefoble_auth.errors import AuthzSchemaError, AuthzUnavailableError, AuthzWriteError
from runefoble_auth.sync import ZitadelSpiceDBSyncService


class CountingSpiceDB:
    """Records every write attempt and raises the preset outcome on each one."""

    def __init__(self, outcome: BaseException) -> None:
        self.outcome = outcome
        self.calls = 0

    async def write_relationship(self, **kwargs: Any) -> None:
        self.calls += 1
        raise self.outcome


class RecoveringSpiceDB:
    """Fails with `AuthzUnavailableError` for the first `failures` attempts, then succeeds."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def write_relationship(self, **kwargs: Any) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise AuthzUnavailableError("SpiceDB did not answer")


def _service(spicedb: Any, max_retries: int = 3) -> ZitadelSpiceDBSyncService:
    return ZitadelSpiceDBSyncService(
        spicedb_client=spicedb,
        max_retries=max_retries,
        retry_delay_seconds=0.001,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "permanent_error",
    [
        AuthzSchemaError("FAILED_PRECONDITION: unknown relation 'owner'"),
        AuthzWriteError("SpiceDB did not apply the relationship write"),
        KeyError("sync bookkeeping defect"),
    ],
    ids=["schema_rejection", "write_refusal", "defect"],
)
async def test_permanent_failure_is_attempted_once_and_raised(permanent_error: Exception) -> None:
    spicedb = CountingSpiceDB(permanent_error)
    service = _service(spicedb, max_retries=4)

    with pytest.raises(type(permanent_error)):
        await service.sync_character_ownership("char-1", "user-1", "campaign-1")

    assert spicedb.calls == 1


@pytest.mark.asyncio
async def test_unavailable_spicedb_is_retried_up_to_the_configured_attempts() -> None:
    spicedb = CountingSpiceDB(AuthzUnavailableError("SpiceDB did not answer"))
    service = _service(spicedb, max_retries=4)

    with pytest.raises(AuthzUnavailableError):
        await service.sync_character_ownership("char-1", "user-1", "campaign-1")

    assert spicedb.calls == 4


@pytest.mark.asyncio
async def test_unavailable_spicedb_recovers_within_the_retry_budget() -> None:
    spicedb = RecoveringSpiceDB(failures=2)
    service = _service(spicedb, max_retries=3)

    synced = await service.sync_membership("camp-1", "user-1", "player")

    assert spicedb.calls == 3
    assert synced == ["campaign:camp-1#player@user:user-1"]
