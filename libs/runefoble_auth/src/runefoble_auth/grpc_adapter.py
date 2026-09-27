"""gRPC client adapter and request builders for live SpiceDB engine."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from runefoble_auth.mock_spicedb import Relationship

logger = logging.getLogger(__name__)


def create_grpc_client(endpoint: str, token: str, insecure: bool = True) -> Any:
    """Create live SpiceDB gRPC client instance."""
    try:
        from authzed.api.v1 import Client, InsecureClient

        if insecure:
            return InsecureClient(endpoint, token)
        import grpc

        channel_creds = grpc.ssl_channel_credentials()
        call_creds = grpc.access_token_call_credentials(token)
        creds = grpc.composite_channel_credentials(channel_creds, call_creds)
        return Client(endpoint, creds)
    except (ImportError, Exception) as exc:
        logger.debug("SpiceDB gRPC client unavailable (%s); using in-memory mock fallback.", exc)
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

    spicedb_relation = "game_master" if relation == "gm" else relation
    update = RelationshipUpdate(
        operation=RelationshipUpdate.OPERATION_TOUCH,
        relationship=AuthzedRelationship(
            resource=ObjectReference(object_type=resource_type, object_id=resource_id),
            relation=spicedb_relation,
            subject=SubjectReference(
                object=ObjectReference(object_type=subject_type, object_id=subject_id)
            ),
        ),
    )
    await invoke_fn("WriteRelationships", WriteRelationshipsRequest(updates=[update]))


async def grpc_delete_relationship(
    invoke_fn: Any,
    resource_type: str,
    resource_id: str,
    relation: str,
    subject_type: str,
    subject_id: str,
) -> None:
    from authzed.api.v1 import DeleteRelationshipsRequest, RelationshipFilter, SubjectFilter

    spicedb_relation = "game_master" if relation == "gm" else relation
    request = DeleteRelationshipsRequest(
        relationship_filter=RelationshipFilter(
            resource_type=resource_type,
            optional_resource_id=resource_id,
            optional_relation=spicedb_relation,
            optional_subject_filter=SubjectFilter(
                subject_type=subject_type, optional_subject_id=subject_id
            ),
        )
    )
    await invoke_fn("DeleteRelationships", request)


async def grpc_read_relationships(
    client: Any, resource_type: str, resource_id: str | None = None, relation: str | None = None
) -> list[Relationship]:
    from authzed.api.v1 import ReadRelationshipsRequest, RelationshipFilter

    spicedb_rel = "game_master" if relation == "gm" else (relation or "")
    rf = RelationshipFilter(
        resource_type=resource_type,
        optional_resource_id=resource_id or "",
        optional_relation=spicedb_rel,
    )
    request = ReadRelationshipsRequest(relationship_filter=rf)

    def _stream_sync() -> list[Relationship]:
        items: list[Relationship] = []
        for resp in client.ReadRelationships(request):
            rel = resp.relationship
            items.append(
                Relationship(
                    resource_type=rel.resource.object_type,
                    resource_id=rel.resource.object_id,
                    relation="gm" if rel.relation == "game_master" else rel.relation,
                    subject_type=rel.subject.object.object_type,
                    subject_id=rel.subject.object.object_id,
                )
            )
        return items

    return await asyncio.to_thread(_stream_sync)


async def grpc_write_schema(invoke_fn: Any, schema_text: str) -> None:
    from authzed.api.v1 import WriteSchemaRequest

    await invoke_fn("WriteSchema", WriteSchemaRequest(schema=schema_text))


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
    from authzed.api.v1 import (
        CheckPermissionRequest,
        CheckPermissionResponse,
        ObjectReference,
        SubjectReference,
    )

    spicedb_perm = "game_master" if permission == "gm" else permission
    request = CheckPermissionRequest(
        resource=ObjectReference(object_type=resource_type, object_id=resource_id),
        permission=spicedb_perm,
        subject=SubjectReference(
            object=ObjectReference(object_type=subject_type, object_id=subject_id)
        ),
    )
    response = await invoke_fn("CheckPermission", request)
    return response.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
