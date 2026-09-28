"""FastAPI route dependencies for settlement haven and establishment authentication.

Governed by ADR-0001, ADR-0005, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Header, Request
from game_session.settlement.auth.permissions import (
    check_establishment_write_permission,
    check_settlement_read_permission,
    check_settlement_write_permission,
)
from game_session.settlement.auth.tokens import AuthenticatedUser, decode_settlement_token


def _get_spicedb() -> Any:
    from game_session.dependencies import get_spicedb_client

    return get_spicedb_client()


async def get_current_settlement_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> AuthenticatedUser:
    """FastAPI dependency extracting authenticated settlement user context."""
    return decode_settlement_token(authorization=authorization, x_user_id=x_user_id)


def require_haven_viewer(param_name: str = "settlement_id") -> Callable:
    """Dependency factory verifying caller has permission to view a haven."""

    async def _dependency(
        request: Request,
        user: Annotated[AuthenticatedUser, Depends(get_current_settlement_user)],
        spicedb: Annotated[Any, Depends(_get_spicedb)],
    ) -> AuthenticatedUser:
        settlement_id = request.path_params.get(param_name)
        if settlement_id:
            await check_settlement_read_permission(spicedb, settlement_id, user.user_id)
        return user

    return _dependency


def require_haven_builder(param_name: str = "settlement_id") -> Callable:
    """Dependency factory verifying caller has permission to construct/upgrade in a haven."""

    async def _dependency(
        request: Request,
        user: Annotated[AuthenticatedUser, Depends(get_current_settlement_user)],
        spicedb: Annotated[Any, Depends(_get_spicedb)],
    ) -> AuthenticatedUser:
        settlement_id = request.path_params.get(param_name)
        if settlement_id:
            await check_settlement_write_permission(spicedb, settlement_id, user.user_id)
        return user

    return _dependency


def require_establishment_manager(param_name: str = "establishment_id") -> Callable:
    """Dependency factory verifying caller has permission to manage an establishment."""

    async def _dependency(
        request: Request,
        user: Annotated[AuthenticatedUser, Depends(get_current_settlement_user)],
        spicedb: Annotated[Any, Depends(_get_spicedb)],
    ) -> AuthenticatedUser:
        establishment_id = request.path_params.get(param_name)
        if establishment_id:
            await check_establishment_write_permission(spicedb, establishment_id, user.user_id)
        return user

    return _dependency


__all__ = [
    "get_current_settlement_user",
    "require_establishment_manager",
    "require_haven_builder",
    "require_haven_viewer",
]
