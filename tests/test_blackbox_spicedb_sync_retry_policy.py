"""Retry policy of the SpiceDB identity sync service (TASK-0853).

Only `AuthzUnavailableError` (a transport failure) is retried. A schema rejection, a failed
write, and any other exception are permanent and propagate on the first attempt.

The counting double stands in for the SpiceDB client at the process boundary. The tests
call the public sync methods and assert the observable outcome: the number of attempts and
the typed error that the caller receives.
"""

from __future__ import annotations

from typing import Any

import grpc
import pytest
from runefoble_auth.errors import (
    AuthzSchemaError,
    AuthzUnavailableError,
    AuthzWriteError,
    AuthzWriteUnavailableError,
)
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.sync import ZitadelSpiceDBSyncService

from tests.helpers.sync_verifier import sync_test_verifier


class FakeRpcError(grpc.RpcError):
    """A gRPC failure with a status code, as the authzed stub raises it."""

    def __init__(self, status: grpc.StatusCode, details: str) -> None:
        super().__init__(details)
        self._status = status
        self._details = details

    def code(self) -> grpc.StatusCode:
        return self._status

    def details(self) -> str:
        return self._details


class WriteStub:
    """Stands in for the SpiceDB gRPC stub at the process boundary.

    Each WriteRelationships call raises the next preset failure. Once the presets run out,
    the call succeeds.
    """

    def __init__(self, failures: list[BaseException]) -> None:
        self.failures = list(failures)
        self.calls = 0

    def WriteRelationships(self, request: Any) -> Any:  # noqa: N802 - gRPC method name
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return None


def _grpc_service(stub: WriteStub, max_retries: int = 3) -> ZitadelSpiceDBSyncService:
    client = SpiceDBClient(endpoint="spicedb.test:50051", token="test-token", grpc_client=stub)
    return ZitadelSpiceDBSyncService(
        spicedb_client=client,
        zitadel_auth=sync_test_verifier(),
        max_retries=max_retries,
        retry_delay_seconds=0.001,
    )


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
        zitadel_auth=sync_test_verifier(),
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


@pytest.mark.asyncio
async def test_write_unavailable_over_grpc_is_retried_and_succeeds() -> None:
    stub = WriteStub([FakeRpcError(grpc.StatusCode.UNAVAILABLE, "connection refused")])
    service = _grpc_service(stub, max_retries=3)

    synced = await service.sync_membership("camp-1", "user-1", "player")

    assert stub.calls == 2
    assert synced == ["campaign:camp-1#player@user:user-1"]


@pytest.mark.asyncio
async def test_write_deadline_exceeded_over_grpc_exhausts_the_retry_budget() -> None:
    stub = WriteStub([FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED, "deadline")] * 5)
    service = _grpc_service(stub, max_retries=3)

    with pytest.raises(AuthzWriteUnavailableError, match="DEADLINE_EXCEEDED"):
        await service.sync_membership("camp-1", "user-1", "player")

    assert stub.calls == 3


@pytest.mark.asyncio
async def test_write_permission_denied_over_grpc_is_not_retried() -> None:
    stub = WriteStub([FakeRpcError(grpc.StatusCode.PERMISSION_DENIED, "denied")] * 5)
    service = _grpc_service(stub, max_retries=3)

    with pytest.raises(AuthzWriteError, match="PERMISSION_DENIED") as info:
        await service.sync_membership("camp-1", "user-1", "player")

    assert not isinstance(info.value, AuthzUnavailableError)
    assert stub.calls == 1
