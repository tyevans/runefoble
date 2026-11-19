"""One SpiceDB subject permission check for every HTTP route (ADR-0001, TASK-0817).

Services call `check_subject` or `require_subject` with a schema resource type, a schema
permission name, and the verified user id. Routes that name the resource by a path parameter
use `require_permission`, which builds a route dependency on the same check. Services never
write their own copy of the lookup.

- A denial is `SpiceDB answered no`. `require_subject` raises `PermissionDenied`, a 403.
- A SpiceDB failure is not a denial. It raises `AuthzError`, which the authz handlers map
  to 503 (TASK-0813). This module never turns a failure into `False`.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization (fail closed)
- Hard Invariant 1: check schema permission names, never roles
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException

from runefoble_auth.factory import get_spicedb_client

DenialFactory = Callable[[str, str, str, str], HTTPException]
"""Build the 403 for (resource_type, resource_id, permission, user_id)."""


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
        resource_type=resource_type,
        resource_id=str(resource_id),
        permission=permission,
        subject_type="user",
        subject_id=str(user_id),
    )


async def require_subject(
    spicedb: Any,
    resource_type: str,
    resource_id: str,
    permission: str,
    user_id: str,
    *,
    detail: str | None = None,
    denial: DenialFactory | None = None,
) -> None:
    """Raise a 403 unless `user_id` holds `permission` on the resource.

    The 403 carries the standard detail. Pass `detail` when a route must keep its own wording,
    or `denial` when it must keep its own body.
    """
    if await check_subject(spicedb, resource_type, resource_id, permission, user_id):
        return
    if denial is not None:
        raise denial(resource_type, str(resource_id), permission, str(user_id))
    raise PermissionDenied(
        detail or denial_detail(resource_type, str(resource_id), permission, str(user_id))
    )


def require_permission(
    resource_type: str,
    permission: str,
    id_param: str,
    *,
    principal: Callable[..., Awaitable[Any]],
    allow_service: bool = False,
    id_type: type = str,
    denial: DenialFactory | None = None,
) -> Callable[..., Awaitable[None]]:
    """Build a route dependency that checks one schema permission on a path resource.

    The check runs before the handler. `principal` is the service's identity dependency.
    It returns an object with a `user_id` attribute. With `allow_service`, a call that has no
    user id (the service credential) passes. Without it, a call with no user is denied.
    `id_type` sets the type of the path parameter. A failed SpiceDB call raises `AuthzError`.
    """

    async def _check(**values: Any) -> None:
        caller = values["principal"]
        user_id = caller.user_id
        if user_id is None and allow_service:
            return
        if user_id is None:
            # No user and no service pass: the call is denied (fail closed).
            raise (denial or _standard_denial)(
                resource_type, str(values[id_param]), permission, "anonymous"
            )
        await require_subject(
            values["spicedb"],
            resource_type,
            str(values[id_param]),
            permission,
            user_id,
            denial=denial,
        )

    _check.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        [
            inspect.Parameter(id_param, inspect.Parameter.KEYWORD_ONLY, annotation=id_type),
            inspect.Parameter(
                "principal",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Annotated[Any, Depends(principal)],
            ),
            inspect.Parameter(
                "spicedb",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Annotated[Any, Depends(get_spicedb_client)],
            ),
        ]
    )
    return _check


def _standard_denial(
    resource_type: str, resource_id: str, permission: str, user_id: str
) -> HTTPException:
    return PermissionDenied(denial_detail(resource_type, resource_id, permission, user_id))


__all__ = [
    "DenialFactory",
    "PermissionDenied",
    "check_subject",
    "denial_detail",
    "require_permission",
    "require_subject",
]
