"""Zanzibar Authorization Dependency and Client for Gateway API."""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Header, HTTPException, Request
from runefoble_auth.spicedb import SpiceDBClient

logger = logging.getLogger("runefoble.gateway.auth")

# Default global SpiceDB client for the gateway
_spicedb_client = SpiceDBClient()


def get_spicedb_client() -> SpiceDBClient:
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient) -> None:
    global _spicedb_client
    _spicedb_client = client


def require_zanzibar_permission(
    permission: str,
    resource_type: str = "campaign",
    resource_param: str = "session_id",
) -> Callable:
    """FastAPI dependency factory enforcing Zanzibar permissions on a resource."""

    async def _checker(
        request: Request,
        x_user_id: str | None = Header(None, alias="X-User-Id"),
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        client = get_spicedb_client()
        user_id = x_user_id

        # Extract subject from bearer token if present and no explicit header
        if not user_id and authorization and authorization.startswith("Bearer "):
            token = authorization[7:].strip()
            user_id = token

        # Default fallback for unauthenticated guest
        if not user_id:
            user_id = "guest_user"

        # Resolve resource ID from path parameters
        resource_id = (
            request.path_params.get(resource_param)
            or request.path_params.get("session_id")
            or "default_resource"
        )

        allowed = await client.check_permission(
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
            subject_type="user",
            subject_id=user_id,
        )

        if not allowed:
            logger.warning(
                "Access denied: user '%s' lacks '%s' on %s:%s",
                user_id,
                permission,
                resource_type,
                resource_id,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "permission_denied",
                    "message": f"Subject 'user:{user_id}' lacks '{permission}' on '{resource_type}:{resource_id}'.",
                    "required_permission": permission,
                    "resource": f"{resource_type}:{resource_id}",
                    "subject": f"user:{user_id}",
                },
            )

        return {"user_id": user_id, "permission": permission, "resource_id": resource_id}

    return _checker
