"""Zanzibar Authorization and Zitadel OIDC Authentication for Gateway API."""

import logging
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.principal import (
    VerifiedPrincipal,
    authenticate_authorization,
    require_principal,
)
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.gateway.auth")

# The gateway uses the shared SpiceDB client factory. It holds no mock wiring.
_zitadel_auth_service: ZitadelAuthService | None = None


def get_zitadel_auth_service() -> ZitadelAuthService:
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        settings = PlatformSettings()
        _zitadel_auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            audience=settings.zitadel_audience,
            jwks_url=settings.zitadel_jwks_url,
        )
    return _zitadel_auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    global _zitadel_auth_service
    _zitadel_auth_service = service


get_current_user = require_principal(get_zitadel_auth_service)

# Route parameter type: the verified principal for an authenticated request.
CurrentPrincipal = Annotated[VerifiedPrincipal, Depends(get_current_user)]


def require_zanzibar_permission(
    permission: str,
    resource_type: str = "campaign",
    resource_param: str = "session_id",
) -> Callable:
    """FastAPI dependency factory enforcing Zanzibar permissions on a resource."""

    async def _checker(
        request: Request,
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        principal = authenticate_authorization(get_zitadel_auth_service(), authorization)
        user_id = principal.user_id
        request.state.principal = principal

        client = get_spicedb_client()

        # Resolve resource ID from path parameters or query parameters
        resource_id = (
            request.path_params.get(resource_param)
            or request.path_params.get("character_id")
            or request.path_params.get("id")
            or request.path_params.get("campaign_id")
            or request.path_params.get("session_id")
            or request.query_params.get("character_id")
            or request.query_params.get("campaign_id")
            or request.query_params.get("session_id")
            or "default_resource"
        )

        try:
            allowed = await client.check_permission(
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
                subject_type="user",
                subject_id=user_id,
            )
        except AuthzUnavailableError as exc:
            logger.error(
                "Authorization unavailable for '%s' on %s:%s",
                permission,
                resource_type,
                resource_id,
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "authorization_unavailable",
                    "message": "Authorization service is unavailable.",
                },
            ) from exc

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

        return {
            "user_id": user_id,
            "permission": permission,
            "resource_id": resource_id,
            "user": principal,
        }

    return _checker
