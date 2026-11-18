"""Runefoble Auth Library."""

from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.principal import (
    BearerVerifier,
    TokenVerificationError,
    VerifiedPrincipal,
    authenticate_authorization,
    require_principal,
)
from runefoble_auth.spicedb import MockSpiceDBClient, Relationship, SpiceDBClient
from runefoble_auth.sync import SyncResult, ZitadelSpiceDBSyncService
from runefoble_auth.websocket import (
    WebSocketAuthError,
    action_authorizer,
    admit_websocket,
    authenticate_websocket,
    send_socket_error,
    verify_websocket,
)
from runefoble_auth.zitadel import ZitadelAuthService

__all__ = [
    "SpiceDBClient",
    "MockSpiceDBClient",
    "Relationship",
    "BearerVerifier",
    "VerifiedPrincipal",
    "ZitadelAuthService",
    "TokenVerificationError",
    "authenticate_authorization",
    "action_authorizer",
    "admit_websocket",
    "authenticate_websocket",
    "send_socket_error",
    "verify_websocket",
    "require_principal",
    "WebSocketAuthError",
    "ZitadelSpiceDBSyncService",
    "SyncResult",
    "bootstrap_schema",
]
