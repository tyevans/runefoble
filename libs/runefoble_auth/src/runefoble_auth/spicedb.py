"""SpiceDB Zanzibar client integration for fine-grained object-level authorization."""

import asyncio
import inspect
import logging
from typing import Any

from runefoble_auth.mock_spicedb import MockSpiceDBClient, Relationship

logger = logging.getLogger(__name__)

__all__ = ["MockSpiceDBClient", "Relationship", "SpiceDBClient"]


class SpiceDBClient(MockSpiceDBClient):
    """Client for querying and writing permissions to SpiceDB Zanzibar engine.

    Supports live SpiceDB gRPC connection when available, with automatic mock fallback.
    """

    def __init__(
        self,
        endpoint: str = "localhost:50051",
        token: str = "secret",
        use_mock: bool | None = None,
        insecure: bool = True,
        grpc_client: Any = None,
    ):
        super().__init__(endpoint=endpoint, token=token)
        self.use_mock = use_mock
        self.insecure = insecure
        self._grpc_client = grpc_client
        if self._grpc_client is None and not self.use_mock:
            self._init_grpc_client()

    def _init_grpc_client(self) -> None:
        try:
            from authzed.api.v1 import Client, InsecureClient

            if self.insecure:
                self._grpc_client = InsecureClient(self.endpoint, self.token)
            else:
                import grpc

                channel_creds = grpc.ssl_channel_credentials()
                call_creds = grpc.access_token_call_credentials(self.token)
                creds = grpc.composite_channel_credentials(channel_creds, call_creds)
                self._grpc_client = Client(self.endpoint, creds)
        except (ImportError, Exception) as exc:
            logger.debug(
                "SpiceDB gRPC client unavailable (%s); using in-memory mock fallback.", exc
            )
            self._grpc_client = None

    async def _invoke_client(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a gRPC method on the client, supporting both sync and async stubs."""
        func = getattr(self._grpc_client, method_name)
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        result = await asyncio.to_thread(func, *args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def write_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        if self._grpc_client is not None:
            try:
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
                request = WriteRelationshipsRequest(updates=[update])
                await self._invoke_client("WriteRelationships", request)
            except Exception as e:
                logger.warning("SpiceDB gRPC write failed, falling back to mock: %s", e)

        await super().write_relationship(
            resource_type, resource_id, relation, subject_type, subject_id
        )

    async def delete_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        if self._grpc_client is not None:
            try:
                from authzed.api.v1 import (
                    DeleteRelationshipsRequest,
                    RelationshipFilter,
                    SubjectFilter,
                )

                spicedb_relation = "game_master" if relation == "gm" else relation
                request = DeleteRelationshipsRequest(
                    relationship_filter=RelationshipFilter(
                        resource_type=resource_type,
                        optional_resource_id=resource_id,
                        optional_relation=spicedb_relation,
                        optional_subject_filter=SubjectFilter(
                            subject_type=subject_type,
                            optional_subject_id=subject_id,
                        ),
                    )
                )
                await self._invoke_client("DeleteRelationships", request)
            except Exception as e:
                logger.warning("SpiceDB gRPC delete failed, falling back to mock: %s", e)

        await super().delete_relationship(
            resource_type, resource_id, relation, subject_type, subject_id
        )

    async def read_relationships(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        relation: str | None = None,
    ) -> list[Relationship]:
        if self._grpc_client is not None and resource_type is not None:
            try:
                from authzed.api.v1 import ReadRelationshipsRequest, RelationshipFilter

                spicedb_relation = "game_master" if relation == "gm" else (relation or "")
                rf = RelationshipFilter(
                    resource_type=resource_type,
                    optional_resource_id=resource_id or "",
                    optional_relation=spicedb_relation,
                )
                request = ReadRelationshipsRequest(relationship_filter=rf)

                def _stream_sync() -> list[Relationship]:
                    items: list[Relationship] = []
                    for resp in self._grpc_client.ReadRelationships(request):
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
            except Exception as e:
                logger.warning("SpiceDB gRPC read failed, falling back to mock: %s", e)

        return await super().read_relationships(
            resource_type=resource_type, resource_id=resource_id, relation=relation
        )

    async def write_schema(self, schema_text: str) -> None:
        """Apply a Zanzibar schema definition to the SpiceDB engine."""
        if self._grpc_client is not None:
            try:
                from authzed.api.v1 import WriteSchemaRequest

                request = WriteSchemaRequest(schema=schema_text)
                await self._invoke_client("WriteSchema", request)
            except Exception as e:
                logger.warning("SpiceDB gRPC write_schema failed, falling back to mock: %s", e)
        await super().write_schema(schema_text)

    async def read_schema(self) -> str:
        """Read the active Zanzibar schema definition from SpiceDB."""
        if self._grpc_client is not None:
            try:
                from authzed.api.v1 import ReadSchemaRequest

                request = ReadSchemaRequest()
                response = await self._invoke_client("ReadSchema", request)
                return getattr(response, "schema_text", "")
            except Exception as e:
                logger.warning("SpiceDB gRPC read_schema failed, falling back to mock: %s", e)
        return await super().read_schema()

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        if self._grpc_client is not None:
            try:
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
                response = await self._invoke_client("CheckPermission", request)
                return (
                    response.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
                )
            except Exception as e:
                logger.warning("SpiceDB gRPC check failed, falling back to mock: %s", e)

        return await super().check_permission(
            resource_type, resource_id, permission, subject_type, subject_id
        )
