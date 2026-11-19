"""Permission port of the gateway MCP process (ADR-0001, ADR-0015 a).

The gateway names what it needs: a check, a grant, a revoke, and the campaigns of an object.
The SpiceDB adapter implements the port. Routes and tools map its two domain errors to HTTP
403 or 503 and to tool errors. A failed check is never a success.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from runefoble_auth.errors import AuthzError


class PermissionDenied(Exception):
    """The subject lacks the permission on the object."""


class AuthorizationUnavailable(Exception):
    """The authorization service failed, so the decision is unknown."""


class PermissionChecker(Protocol):
    """What the gateway needs from an authorization service."""

    async def check(
        self, resource_type: str, resource_id: str, permission: str, user_id: str
    ) -> bool:
        """Return whether `user_id` holds `permission` on the object."""
        ...

    async def grant(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Write one relationship."""
        ...

    async def revoke(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Delete one relationship."""
        ...

    async def campaign_ids(self, resource_type: str, resource_id: str) -> list[str]:
        """Return the ids of the campaigns that the object belongs to."""
        ...


class SpiceDBPermissionChecker:
    """Implements `PermissionChecker` on the SpiceDB client of the auth library.

    The client is resolved on each call, so a test that swaps the client sees the swap.
    """

    def __init__(self, resolve_client: Callable[[], Any]) -> None:
        self._resolve_client = resolve_client

    async def check(
        self, resource_type: str, resource_id: str, permission: str, user_id: str
    ) -> bool:
        try:
            return await self._resolve_client().check_permission(
                resource_type, resource_id, permission, "user", user_id
            )
        except AuthzError as exc:
            raise AuthorizationUnavailable from exc

    async def grant(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        try:
            await self._resolve_client().write_relationship(
                resource_type, resource_id, relation, subject_type, subject_id
            )
        except AuthzError as exc:
            raise AuthorizationUnavailable from exc

    async def revoke(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        try:
            await self._resolve_client().delete_relationship(
                resource_type, resource_id, relation, subject_type, subject_id
            )
        except AuthzError as exc:
            raise AuthorizationUnavailable from exc

    async def campaign_ids(self, resource_type: str, resource_id: str) -> list[str]:
        try:
            links = await self._resolve_client().read_relationships(
                resource_type=resource_type, resource_id=resource_id, relation="campaign"
            )
        except AuthzError as exc:
            raise AuthorizationUnavailable from exc
        return [link.subject_id for link in links]
