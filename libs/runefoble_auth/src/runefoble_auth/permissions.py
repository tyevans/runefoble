"""One SpiceDB subject permission check for every HTTP route (ADR-0001, TASK-0817).

Services call `check_subject` or `require_subject` with a schema resource type, a schema
permission name, and the verified user id. They never write their own copy of the lookup.

- A denial is `SpiceDB answered no`. `require_subject` raises `PermissionDenied`, a 403.
- A SpiceDB failure is not a denial. It raises `AuthzError`, which the authz handlers map
  to 503 (TASK-0813). This module never turns a failure into `False`.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization (fail closed)
- Hard Invariant 1: check schema permission names, never roles
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class PermissionDenied(HTTPException):
    """HTTP 403 for a subject that lacks a schema permission on a resource."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=403, detail=detail)


def denial_detail(resource_type: str, resource_id: str, permission: str, user_id: str) -> str:
    """Return the standard 403 detail. It names the subject, the permission, and the resource."""
    return (
        f"Permission denied: subject '{user_id}' lacks '{permission}' on "
        f"{resource_type}:{resource_id}"
    )


async def check_subject(
    spicedb: Any,
    resource_type: str,
    resource_id: str,
    permission: str,
    user_id: str,
) -> bool:
    """Return whether `user_id` holds `permission` on the resource. A failure raises."""
    return await spicedb.check_permission(
        resource_type, str(resource_id), permission, "user", str(user_id)
    )


async def require_subject(
    spicedb: Any,
    resource_type: str,
    resource_id: str,
    permission: str,
    user_id: str,
    *,
    detail: str | None = None,
) -> None:
    """Raise `PermissionDenied` (403) unless `user_id` holds `permission` on the resource.

    Pass `detail` only when a route must keep its own denial wording.
    """
    if not await check_subject(spicedb, resource_type, resource_id, permission, user_id):
        raise PermissionDenied(
            detail or denial_detail(resource_type, str(resource_id), permission, str(user_id))
        )


__all__ = [
    "PermissionDenied",
    "check_subject",
    "denial_detail",
    "require_subject",
]
