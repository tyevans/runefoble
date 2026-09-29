"""Zanzibar Authorization and Zitadel OIDC Authentication for Gateway API."""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Header, HTTPException, Request
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import AuthenticatedUser, ZitadelAuthService
from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.gateway.auth")

# Default global clients for the gateway
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None
_zitadel_auth_service: ZitadelAuthService | None = None


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    global _spicedb_client
    if _spicedb_client is None:
        settings = PlatformSettings()
        _spicedb_client = SpiceDBClient(
            endpoint=settings.spicedb_endpoint,
            token=settings.spicedb_preshared_key,
        )
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    global _spicedb_client
    _spicedb_client = client


def get_zitadel_auth_service() -> ZitadelAuthService:
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        settings = PlatformSettings()
        _zitadel_auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            client_id=settings.zitadel_client_id,
            jwks_url=settings.zitadel_jwks_url,
            dev_mode=settings.auth_dev_mode,
        )
    return _zitadel_auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    global _zitadel_auth_service
    _zitadel_auth_service = service


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> AuthenticatedUser:
    """Dependency that extracts and validates the authenticated Zitadel user."""
    auth_service = get_zitadel_auth_service()

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        try:
            user = auth_service.verify_token(token)
            request.state.user = user
            return user
        except Exception as exc:
            logger.warning("Bearer token verification failed: %s", exc)
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": f"Token verification failed: {exc}",
                },
            ) from exc

    if auth_service.dev_mode:
        effective_id = x_user_id or "dev-user-001"
        dev_user = AuthenticatedUser(
            user_id=effective_id,
            username=effective_id,
            roles=["player", "dm"],
            is_admin=True,
        )
        request.state.user = dev_user
        return dev_user

    raise HTTPException(
        status_code=401,
        detail={
            "error": "unauthorized",
            "message": "Missing or invalid Bearer token",
        },
    )


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
        auth_service = get_zitadel_auth_service()
        user_id: str | None = None
        authenticated_user: AuthenticatedUser | None = None

        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:].strip()
            try:
                authenticated_user = auth_service.verify_token(token)
                user_id = authenticated_user.user_id
                request.state.user = authenticated_user
            except Exception as exc:
                logger.warning("Token verification failed in require_zanzibar_permission: %s", exc)
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "unauthorized",
                        "message": f"Token verification failed: {exc}",
                    },
                ) from exc
        elif auth_service.dev_mode:
            user_id = x_user_id or "guest_user"
            authenticated_user = AuthenticatedUser(
                user_id=user_id,
                username=user_id,
                roles=["player", "dm"],
                is_admin=True,
            )
            request.state.user = authenticated_user
        else:
            logger.warning(
                "Authentication failed: Missing or invalid Bearer token in production mode"
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": "Authentication required: missing or unverified Bearer token",
                },
            )

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

        if resource_type == "campaign":
            from gateway_api.campaign_store import campaign_store

            sess = campaign_store.get_session(resource_id)
            if sess:
                resource_id = sess.campaign_id

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

        return {
            "user_id": user_id,
            "permission": permission,
            "resource_id": resource_id,
            "user": authenticated_user,
        }

    return _checker
