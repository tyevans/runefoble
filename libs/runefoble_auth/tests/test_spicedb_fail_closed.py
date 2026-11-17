"""Fail-closed SpiceDB client behaviour (TASK-0541).

A transport failure, a schema error, or a failed write must raise a typed error.
Only a definitive NO_PERMISSION answer may return False.

Governed by:
- ADR-0001: SpiceDB is the only object-permission authority.
- ADR-0007: the library owns the client.
- Hard Invariant 7: tests use the public client surface. The fake stub stands in
  for the external gRPC process, which is a true process boundary.
"""

from __future__ import annotations

from typing import Any

import grpc
import pytest
from authzed.api.v1 import CheckPermissionResponse
from runefoble_auth.errors import (
    AuthzError,
    AuthzSchemaError,
    AuthzUnavailableError,
    AuthzWriteError,
)
from runefoble_auth.spicedb import SpiceDBClient


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


class FakeStub:
    """Stands in for the SpiceDB gRPC stub. Each method returns or raises a preset outcome."""

    def __init__(self, outcome: Any = None) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, Any]] = []

    def _respond(self, method: str, request: Any) -> Any:
        self.calls.append((method, request))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome

    def CheckPermission(self, request: Any) -> Any:  # noqa: N802 - gRPC method name
        return self._respond("CheckPermission", request)

    def WriteRelationships(self, request: Any) -> Any:  # noqa: N802
        return self._respond("WriteRelationships", request)

    def DeleteRelationships(self, request: Any) -> Any:  # noqa: N802
        return self._respond("DeleteRelationships", request)

    def WriteSchema(self, request: Any) -> Any:  # noqa: N802
        return self._respond("WriteSchema", request)


def _client(outcome: Any = None) -> tuple[SpiceDBClient, FakeStub]:
    stub = FakeStub(outcome)
    return SpiceDBClient(endpoint="fake:50051", token="test-key", grpc_client=stub), stub


def _permission(value: int) -> CheckPermissionResponse:
    return CheckPermissionResponse(permissionship=value)


async def _check(client: SpiceDBClient) -> bool:
    return await client.check_permission("campaign", "c1", "view", "user", "u1")


# --- check_permission -----------------------------------------------------------


@pytest.mark.asyncio
async def test_check_raises_unavailable_instead_of_returning_false() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.UNAVAILABLE, "connection refused"))
    with pytest.raises(AuthzUnavailableError, match="UNAVAILABLE"):
        await _check(client)


@pytest.mark.asyncio
async def test_check_raises_unavailable_on_deadline_exceeded() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED, "deadline"))
    with pytest.raises(AuthzUnavailableError, match="DEADLINE_EXCEEDED"):
        await _check(client)


@pytest.mark.asyncio
async def test_check_raises_unavailable_on_socket_error() -> None:
    client, _ = _client(ConnectionError("socket closed"))
    with pytest.raises(AuthzUnavailableError):
        await _check(client)


@pytest.mark.asyncio
async def test_check_raises_schema_error_for_undefined_permission() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, "undefined permission"))
    with pytest.raises(AuthzSchemaError, match="INVALID_ARGUMENT"):
        await _check(client)


@pytest.mark.asyncio
async def test_check_raises_schema_error_for_failed_precondition() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.FAILED_PRECONDITION, "not found"))
    with pytest.raises(AuthzSchemaError, match="FAILED_PRECONDITION"):
        await _check(client)


@pytest.mark.asyncio
async def test_check_raises_on_unexpected_status_instead_of_returning_false() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.INTERNAL, "boom"))
    with pytest.raises(AuthzError, match="INTERNAL"):
        await _check(client)


@pytest.mark.asyncio
async def test_check_raises_on_conditional_answer() -> None:
    """A conditional answer is neither allowed nor denied, so the client does not guess."""
    client, _ = _client(_permission(CheckPermissionResponse.PERMISSIONSHIP_CONDITIONAL_PERMISSION))
    with pytest.raises(AuthzError, match="CONDITIONAL"):
        await _check(client)


@pytest.mark.asyncio
async def test_check_returns_false_only_for_no_permission() -> None:
    client, _ = _client(_permission(CheckPermissionResponse.PERMISSIONSHIP_NO_PERMISSION))
    assert await _check(client) is False


@pytest.mark.asyncio
async def test_check_returns_true_when_permission_is_granted() -> None:
    client, _ = _client(_permission(CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION))
    assert await _check(client) is True


# --- writes and deletes ---------------------------------------------------------


@pytest.mark.asyncio
async def test_write_relationship_raises_write_error_on_transport_failure() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down"))
    with pytest.raises(AuthzWriteError, match="UNAVAILABLE"):
        await client.write_relationship("campaign", "c1", "player", "user", "u1")


@pytest.mark.asyncio
async def test_touch_relationship_raises_write_error_on_failure() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down"))
    with pytest.raises(AuthzWriteError):
        await client.touch_relationship("campaign", "c1", "player", "user", "u1")


@pytest.mark.asyncio
async def test_delete_relationship_raises_write_error_on_failure() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down"))
    with pytest.raises(AuthzWriteError):
        await client.delete_relationship("campaign", "c1", "player", "user", "u1")


@pytest.mark.asyncio
async def test_write_schema_raises_write_error_on_failure() -> None:
    client, _ = _client(FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down"))
    with pytest.raises(AuthzWriteError):
        await client.write_schema("definition user {}")


@pytest.mark.asyncio
async def test_write_with_undefined_relation_raises_schema_error() -> None:
    """The adapter sends the schema name unchanged. 'gm' is not a schema relation."""
    client, stub = _client(FakeRpcError(grpc.StatusCode.FAILED_PRECONDITION, "relation gm"))
    with pytest.raises(AuthzSchemaError):
        await client.write_relationship("campaign", "c1", "gm", "user", "u1")
    method, request = stub.calls[0]
    assert method == "WriteRelationships"
    assert request.updates[0].relationship.relation == "gm"


@pytest.mark.asyncio
async def test_delete_sends_schema_relation_name_unchanged() -> None:
    client, stub = _client(None)
    await client.delete_relationship("campaign", "c1", "game_master", "user", "u1")
    _, request = stub.calls[0]
    assert request.relationship_filter.optional_relation == "game_master"


@pytest.mark.asyncio
async def test_check_sends_schema_permission_name_unchanged() -> None:
    client, stub = _client(_permission(CheckPermissionResponse.PERMISSIONSHIP_NO_PERMISSION))
    await client.check_permission("campaign", "c1", "gm", "user", "u1")
    _, request = stub.calls[0]
    assert request.permission == "gm"


# --- error hierarchy ------------------------------------------------------------


def test_typed_errors_share_one_base_and_keep_status_in_message() -> None:
    assert issubclass(AuthzUnavailableError, AuthzError)
    assert issubclass(AuthzSchemaError, AuthzError)
    assert issubclass(AuthzWriteError, AuthzError)
    error = AuthzUnavailableError("UNAVAILABLE: connection refused")
    assert "UNAVAILABLE" in str(error)
