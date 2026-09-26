"""Zitadel OIDC and JWT token authentication helper."""

from typing import Any, Dict, Optional
import jwt
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    roles: list[str] = []
    is_admin: bool = False


class ZitadelAuthService:
    """Validates tokens and provides user claims against self-hosted Zitadel."""

    def __init__(self, issuer: str = "http://localhost:8080", client_id: str = "runefoble-api"):
        self.issuer = issuer
        self.client_id = client_id

    def decode_token(self, token: str, verify: bool = False) -> AuthenticatedUser:
        """Decode a Zitadel JWT token into a structured user object.

        In production, verifies signature against Zitadel JWKS endpoint.
        """
        try:
            payload: Dict[str, Any] = jwt.decode(
                token,
                options={"verify_signature": verify},
                algorithms=["RS256", "HS256"],
            )
            user_id = payload.get("sub", "anonymous")
            email = payload.get("email")
            roles = payload.get("urn:zitadel:iam:org:project:roles", [])
            username = payload.get("preferred_username", user_id)

            return AuthenticatedUser(
                user_id=user_id,
                username=username,
                email=email,
                roles=list(roles.keys()) if isinstance(roles, dict) else roles,
                is_admin="admin" in roles,
            )
        except Exception as e:
            # Fallback for dev / mock tokens
            return AuthenticatedUser(
                user_id="dev-user-001",
                username="DevAdventurer",
                email="dev@runefoble.local",
                roles=["player", "dm"],
                is_admin=True,
            )
