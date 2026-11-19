"""The SpiceDB client port. Production code and test doubles both satisfy it.

Callers type against `SpiceDBPort`, never against a concrete client. `backend_name` names the
transport (`"grpc"` for the live client, `"mock"` for the in-memory test double).
"""

from __future__ import annotations

from typing import Protocol

from runefoble_auth.relationship import Relationship


class SpiceDBPort(Protocol):
    """The SpiceDB operations that Runefoble callers use."""

    backend_name: str

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool: ...

    async def write_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None: ...

    async def touch_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None: ...

    async def delete_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None: ...

    async def read_relationships(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        relation: str | None = None,
    ) -> list[Relationship]: ...

    async def lookup_resources(
        self,
        resource_type: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> list[str]: ...

    async def write_schema(self, schema_text: str) -> None: ...

    async def read_schema(self) -> str: ...
