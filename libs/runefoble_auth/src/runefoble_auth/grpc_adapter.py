"""gRPC client adapter and request builders for live SpiceDB engine."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import grpc

from runefoble_auth.errors import (
    AuthzError,
    AuthzSchemaError,
    AuthzUnavailableError,
    AuthzWriteError,
)
from runefoble_auth.mock.client import Relationship

logger = logging.getLogger(__name__)

_UNAVAILABLE_CODES = frozenset({grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED})
_SCHEMA_CODES = frozenset({grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.FAILED_PRECONDITION})


def create_grpc_client(endpoint: str, token: str, insecure: bool = True) -> Any:
    """Create live SpiceDB gRPC client instance."""
    from authzed.api.v1 import Client, InsecureClient

    if insecure:
        return InsecureClient(endpoint, token)
    channel_creds = grpc.ssl_channel_credentials()
    call_creds = grpc.access_token_call_credentials(token)
    creds = grpc.composite_channel_credentials(channel_creds, call_creds)
    return Client(endpoint, creds)


def _describe(exc: BaseException) -> str:
    if isinstance(exc, grpc.RpcError):
        return f"{exc.code().name}: {exc.details()}"
    return f"{type(exc).__name__}: {exc}"


def check_error_for(exc: BaseException, operation: str) -> AuthzError | None:
    """Translate a failed check call into a typed error. Return None for other exceptions."""
    if isinstance(exc, grpc.RpcError):
        code = exc.code()
        if code in _UNAVAILABLE_CODES:
            return AuthzUnavailableError(f"{operation} failed. {_describe(exc)}")
        if code in _SCHEMA_CODES:
            return AuthzSchemaError(f"{operation} rejected by schema. {_describe(exc)}")
        return AuthzError(f"{operation} failed. {_describe(exc)}")
    if isinstance(exc, ConnectionError | TimeoutError):
        return AuthzUnavailableError(f"{operation} failed. {_describe(exc)}")
    return None


def write_error_for(exc: BaseException, operation: str) -> AuthzError | None:
    """Translate a failed write, delete, or schema call. Return None for other exceptions."""
    if isinstance(exc, grpc.RpcError) and exc.code() in _SCHEMA_CODES:
        return AuthzSchemaError(f"{operation} rejected by schema. {_describe(exc)}")
    if isinstance(exc, grpc.RpcError | ConnectionError | TimeoutError):
        return AuthzWriteError(f"{operation} failed. {_describe(exc)}")
    return None


async def grpc_write_relationship(
    invoke_fn: Any,
    resource_type: str,
    resource_id: str,
    relation: str,
    subject_type: str,
    subject_id: str,
) -> None:
    from authzed.api.v1 import (
        ObjectReference,
        RelationshipUpdate,
        SubjectReference,
        WriteRelationshipsRequest,
    )
    from authzed.api.v1 import (
        Relationship as AuthzedRelationship,
    )

    update = RelationshipUpdate(
        operation=RelationshipUpdate.OPERATION_TOUCH,
        relationship=AuthzedRelationship(
            resource=ObjectReference(object_type=resource_type, object_id=resource_id),
            relation=relation,
            subject=SubjectReference(
                object=ObjectReference(object_type=subject_type, object_id=subject_id)
            ),
        ),
    )
    try:
        await invoke_fn("WriteRelationships", WriteRelationshipsRequest(updates=[update]))
    except Exception as exc:
        error = write_error_for(exc, "WriteRelationships")
        if error is None:
            raise
        raise error from exc


async def grpc_delete_relationship(
    invoke_fn: Any,
    resource_type: str,
    resource_id: str,
    relation: str,
    subject_type: str,
    subject_id: str,
) -> None:
    from authzed.api.v1 import DeleteRelationshipsRequest, RelationshipFilter, SubjectFilter

    request = DeleteRelationshipsRequest(
        relationship_filter=RelationshipFilter(
            resource_type=resource_type,
            optional_resource_id=resource_id,
            optional_relation=relation,
            optional_subject_filter=SubjectFilter(
                subject_type=subject_type, optional_subject_id=subject_id
            ),
        )
    )
    try:
        await invoke_fn("DeleteRelationships", request)
    except Exception as exc:
        error = write_error_for(exc, "DeleteRelationships")
        if error is None:
            raise
        raise error from exc


async def grpc_read_relationships(
    client: Any, resource_type: str, resource_id: str | None = None, relation: str | None = None
) -> list[Relationship]:
    from authzed.api.v1 import Consistency, ReadRelationshipsRequest, RelationshipFilter

    rf = RelationshipFilter(
        resource_type=resource_type,
        optional_resource_id=resource_id or "",
        optional_relation=relation or "",
    )
    request = ReadRelationshipsRequest(
        relationship_filter=rf,
        consistency=Consistency(fully_consistent=True),
    )

    def _stream_sync() -> list[Relationship]:
        items: list[Relationship] = []
        for resp in client.ReadRelationships(request):
            rel = resp.relationship
            items.append(
                Relationship(
                    resource_type=rel.resource.object_type,
                    resource_id=rel.resource.object_id,
                    relation=rel.relation,
                    subject_type=rel.subject.object.object_type,
                    subject_id=rel.subject.object.object_id,
                )
            )
        return items

    try:
        return await asyncio.to_thread(_stream_sync)
    except Exception as exc:
        error = check_error_for(exc, "ReadRelationships")
        if error is None:
            raise
        raise error from exc


async def grpc_lookup_resources(
    client: Any,
    resource_type: str,
    permission: str,
    subject_type: str,
    subject_id: str,
) -> list[str]:
    """Return the IDs of every resource of `resource_type` where the subject has `permission`."""
    from authzed.api.v1 import (
        Consistency,
        LookupResourcesRequest,
        ObjectReference,
        SubjectReference,
    )

    request = LookupResourcesRequest(
        consistency=Consistency(fully_consistent=True),
        resource_object_type=resource_type,
        permission=permission,
        subject=SubjectReference(
            object=ObjectReference(object_type=subject_type, object_id=subject_id)
        ),
    )

    def _stream_sync() -> list[str]:
        try:
            return [resp.resource_object_id for resp in client.LookupResources(request)]
        except Exception as exc:
            error = check_error_for(exc, "LookupResources")
            if error is None:
                raise
            raise error from exc

    return await asyncio.to_thread(_stream_sync)


async def grpc_write_schema(invoke_fn: Any, schema_text: str) -> None:
    from authzed.api.v1 import WriteSchemaRequest

    try:
        await invoke_fn("WriteSchema", WriteSchemaRequest(schema=schema_text))
    except Exception as exc:
        error = write_error_for(exc, "WriteSchema")
        if error is None:
            raise
        raise error from exc


async def grpc_read_schema(invoke_fn: Any) -> str:
    from authzed.api.v1 import ReadSchemaRequest

    response = await invoke_fn("ReadSchema", ReadSchemaRequest())
    return getattr(response, "schema_text", "")


async def grpc_check_permission(
    invoke_fn: Any,
    resource_type: str,
    resource_id: str,
    permission: str,
    subject_type: str,
    subject_id: str,
) -> bool:
    """Return True or False only for a definitive answer. Raise a typed error otherwise."""
    from authzed.api.v1 import (
        CheckPermissionRequest,
        CheckPermissionResponse,
        Consistency,
        ObjectReference,
        SubjectReference,
    )

    request = CheckPermissionRequest(
        resource=ObjectReference(object_type=resource_type, object_id=resource_id),
        permission=permission,
        subject=SubjectReference(
            object=ObjectReference(object_type=subject_type, object_id=subject_id)
        ),
        consistency=Consistency(fully_consistent=True),
    )
    try:
        response = await invoke_fn("CheckPermission", request)
    except Exception as exc:
        error = check_error_for(exc, "CheckPermission")
        if error is None:
            raise
        raise error from exc

    answer = response.permissionship
    if answer == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
        return True
    if answer == CheckPermissionResponse.PERMISSIONSHIP_NO_PERMISSION:
        return False
    name = CheckPermissionResponse.Permissionship.Name(answer)
    raise AuthzError(
        f"CheckPermission returned an answer that is neither allowed nor denied: {name}"
    )
