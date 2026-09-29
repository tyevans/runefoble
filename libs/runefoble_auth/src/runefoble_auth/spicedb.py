"""SpiceDB Zanzibar client integration for fine-grained object-level authorization."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
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

DEFAULT_SPICEDB_ENDPOINT = os.getenv(
    "RUNEFOBLE_SPICEDB_ENDPOINT", os.getenv("SPICEDB_ENDPOINT", "localhost:50051")
)
DEFAULT_SPICEDB_TOKEN = os.getenv(
    "RUNEFOBLE_SPICEDB_PRESHARED_KEY", os.getenv("SPICEDB_TOKEN", "runefoble_secret_key")
)


class SpiceDBClient:
    """Client for querying and writing permissions to SpiceDB Zanzibar engine over live gRPC."""

    def __init__(
        self,
        endpoint: str = DEFAULT_SPICEDB_ENDPOINT,
        token: str = DEFAULT_SPICEDB_TOKEN,
        use_mock: bool | None = None,
        insecure: bool = True,
        grpc_client: Any = None,
    ):
        if use_mock:
            raise ValueError(
                "SpiceDBClient no longer supports mock fallback. "
                "Use runefoble_auth.spicedb.MockSpiceDBClient directly for offline testing."
            )
        self.endpoint = endpoint
        self.token = token
        self.insecure = insecure
        self._grpc_client = grpc_client
        if self._grpc_client is None:
            self._grpc_client = create_grpc_client(self.endpoint, self.token, self.insecure)

    async def _invoke_client(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a gRPC method on the client, supporting both sync and async stubs."""
        if self._grpc_client is None:
            raise RuntimeError(
                f"SpiceDB gRPC client is not initialized. Cannot invoke '{method_name}' on {self.endpoint}."
            )
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
        await grpc_write_relationship(
            self._invoke_client,
            resource_type,
            resource_id,
            relation,
            subject_type,
            subject_id,
        )

    async def touch_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Touch / upsert a relationship tuple in Zanzibar."""
        await self.write_relationship(
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
        await grpc_delete_relationship(
            self._invoke_client,
            resource_type,
            resource_id,
            relation,
            subject_type,
            subject_id,
        )

    async def read_relationships(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        relation: str | None = None,
    ) -> list[Relationship]:
        if not resource_type:
            raise ValueError("resource_type is required to read SpiceDB relationships")
        if self._grpc_client is None:
            raise RuntimeError(
                f"SpiceDB client not initialized. Cannot read relationships from {self.endpoint}."
            )
        return await grpc_read_relationships(
            self._grpc_client, resource_type, resource_id, relation
        )

    async def write_schema(self, schema_text: str) -> None:
        """Apply a Zanzibar schema definition to the SpiceDB engine."""
        await grpc_write_schema(self._invoke_client, schema_text)

    async def read_schema(self) -> str:
        """Read the active Zanzibar schema definition from SpiceDB."""
        return await grpc_read_schema(self._invoke_client)

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        return await grpc_check_permission(
            self._invoke_client,
            resource_type,
            resource_id,
            permission,
            subject_type,
            subject_id,
        )
