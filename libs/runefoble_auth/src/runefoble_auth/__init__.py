"""Runefoble Auth Library."""

from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.listener import SpiceDBEventListener
from runefoble_auth.principal import (
    BearerVerifier,
    TokenVerificationError,
    VerifiedPrincipal,
    authenticate_authorization,
    require_principal,
)
from runefoble_auth.spicedb import MockSpiceDBClient, Relationship, SpiceDBClient
from runefoble_auth.sync import SyncResult, ZitadelSpiceDBSyncService
from runefoble_auth.websocket import WebSocketAuthError, authenticate_websocket
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
    "authenticate_websocket",
    "require_principal",
    "WebSocketAuthError",
    "ZitadelSpiceDBSyncService",
    "SyncResult",
    "SpiceDBEventListener",
    "bootstrap_schema",
]
