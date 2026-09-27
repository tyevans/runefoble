"""SpiceDB Zanzibar client integration for fine-grained object-level authorization."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

from runefoble_auth.grpc_adapter import (
    create_grpc_client,
    grpc_check_permission,
    grpc_delete_relationship,
    grpc_read_relationships,
    grpc_read_schema,
    grpc_write_relationship,
    grpc_write_schema,
)
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
            self._grpc_client = create_grpc_client(self.endpoint, self.token, self.insecure)

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
                await grpc_write_relationship(
                    self._invoke_client,
                    resource_type,
                    resource_id,
                    relation,
                    subject_type,
                    subject_id,
                )
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
                await grpc_delete_relationship(
                    self._invoke_client,
                    resource_type,
                    resource_id,
                    relation,
                    subject_type,
                    subject_id,
                )
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
                return await grpc_read_relationships(
                    self._grpc_client, resource_type, resource_id, relation
                )
            except Exception as e:
                logger.warning("SpiceDB gRPC read failed, falling back to mock: %s", e)
        return await super().read_relationships(
            resource_type=resource_type, resource_id=resource_id, relation=relation
        )

    async def write_schema(self, schema_text: str) -> None:
        """Apply a Zanzibar schema definition to the SpiceDB engine."""
        if self._grpc_client is not None:
            try:
                await grpc_write_schema(self._invoke_client, schema_text)
            except Exception as e:
                logger.warning("SpiceDB gRPC write_schema failed, falling back to mock: %s", e)
        await super().write_schema(schema_text)

    async def read_schema(self) -> str:
        """Read the active Zanzibar schema definition from SpiceDB."""
        if self._grpc_client is not None:
            try:
                return await grpc_read_schema(self._invoke_client)
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
                return await grpc_check_permission(
                    self._invoke_client,
                    resource_type,
                    resource_id,
                    permission,
                    subject_type,
                    subject_id,
                )
            except Exception as e:
                logger.warning("SpiceDB gRPC check failed, falling back to mock: %s", e)
        return await super().check_permission(
            resource_type, resource_id, permission, subject_type, subject_id
        )
