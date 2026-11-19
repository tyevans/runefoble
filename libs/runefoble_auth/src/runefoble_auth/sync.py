"""Zitadel OIDC and SpiceDB Zanzibar relationship synchronization coordinator."""

from __future__ import annotations

import logging
from typing import Any, Literal
from uuid import UUID

from runefoble_platform.config import PlatformSettings

from runefoble_auth.errors import AuthzError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.mock.client import MockSpiceDBClient, Relationship
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.sync_events import (
    handle_character_created,
    handle_domain_event,
    handle_participant_joined,
    handle_session_created,
    handle_token_placed,
)
from runefoble_auth.sync_tuples import (
    SyncResult,
    batch_write_tuples,
    delete_relationship_tuple,
    execute_with_retry,
    normalize_campaign_role,
    reconcile_tuples,
    write_relationship_tuple,
)
from runefoble_auth.wiring import verifier_from_settings
from runefoble_auth.zitadel import ZitadelAuthService

logger = logging.getLogger(__name__)

# A resource id that no tuple names. The health probe reads it and expects no rows.
HEALTH_PROBE_RESOURCE_ID = "sync-health-probe"


class ZitadelSpiceDBSyncService:
    """Translates identity events and user claims into Zanzibar relationship tuples."""

    def __init__(
        self,
        spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None,
        zitadel_auth: ZitadelAuthService | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 0.05,
    ) -> None:
        self.spicedb = spicedb_client or get_spicedb_client()
        self.zitadel = zitadel_auth or verifier_from_settings(PlatformSettings())
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    async def _execute_with_retry(self, coro_func: Any, *args: Any, **kwargs: Any) -> Any:
        return await execute_with_retry(
            coro_func, self.max_retries, self.retry_delay_seconds, *args, **kwargs
        )

    async def _write_tuple(self, res_t: str, res_id: str, rel: str, sub_t: str, sub_id: str) -> str:
        return await write_relationship_tuple(
            self.spicedb, res_t, res_id, rel, sub_t, sub_id, self._execute_with_retry
        )

    async def _delete_tuple(
        self, res_t: str, res_id: str, rel: str, sub_t: str, sub_id: str
    ) -> str:
        return await delete_relationship_tuple(
            self.spicedb, res_t, res_id, rel, sub_t, sub_id, self._execute_with_retry
        )

    async def sync_membership(
        self,
        campaign_id: str,
        user_id: str,
        role: Literal["game_master", "player", "spectator", "owner"] | str,
        session_id: str | None = None,
        action: Literal["grant", "revoke"] = "grant",
    ) -> list[str]:
        """Grant or revoke campaign or session roles for a given user."""
        if action not in ("grant", "revoke"):
            raise ValueError(f"Unsupported action: {action}")
        fn = self._write_tuple if action == "grant" else self._delete_tuple
        res = [
            await fn("campaign", campaign_id, r, "user", user_id)
            for r in normalize_campaign_role(role)
        ]
        if session_id and action == "grant":
            res.extend(await self.sync_session_campaign(session_id, campaign_id))
        return res

    async def sync_character_ownership(
        self, character_id: str | UUID, user_id: str, campaign_id: str | None = None
    ) -> list[str]:
        t = [("character", str(character_id), "owner", "user", user_id)]
        if campaign_id:
            t.append(("character", str(character_id), "campaign", "campaign", campaign_id))
        return [await self._write_tuple(*x) for x in t]

    async def sync_session_campaign(self, session_id: str | UUID, campaign_id: str) -> list[str]:
        """Write the one campaign link, `game_session#campaign` (ADR-0015 (a))."""
        return [
            await self._write_tuple(
                "game_session", str(session_id), "campaign", "campaign", campaign_id
            )
        ]

    async def sync_board_token(
        self, token_id: str, character_id: str | UUID | None = None, campaign_id: str | None = None
    ) -> list[str]:
        t: list[tuple[str, str, str, str, str]] = []
        if character_id:
            t.append(("board_token", token_id, "character", "character", str(character_id)))
        if campaign_id:
            t.append(("board_token", token_id, "campaign", "campaign", campaign_id))
        return [await self._write_tuple(*x) for x in t]

    async def batch_write_relationships(
        self, relationships: list[tuple[str, str, str, str, str] | Relationship]
    ) -> list[str]:
        return await batch_write_tuples(self._write_tuple, relationships)

    async def reconcile_relationships(
        self, expected_tuples: list[tuple[str, str, str, str, str] | Relationship]
    ) -> dict[str, Any]:
        return await reconcile_tuples(self.spicedb, self._write_tuple, expected_tuples)

    async def check_health(self) -> dict[str, Any]:
        """Report synchronization health and SpiceDB connectivity.

        Only SpiceDB failures (`AuthzError`) become an `unhealthy` reply. Every other exception
        is a defect and propagates. The reply always carries the same four keys.
        """
        is_mock = isinstance(self.spicedb, MockSpiceDBClient) and not getattr(
            self.spicedb, "_grpc_client", None
        )
        backend = "mock" if is_mock else "grpc"
        try:
            await self.spicedb.read_relationships(
                resource_type="campaign", resource_id=HEALTH_PROBE_RESOURCE_ID
            )
        except AuthzError as exc:
            logger.warning("SpiceDB health probe failed: %s", exc)
            return {
                "status": "unhealthy",
                "spicedb_connected": False,
                "sync_service": "unavailable",
                "backend": backend,
                "error": str(exc),
            }
        return {
            "status": "healthy",
            "spicedb_connected": True,
            "sync_service": "operational",
            "backend": backend,
        }

    async def handle_domain_event(self, event: Any, campaign_id: str | None = None) -> list[str]:
        return await handle_domain_event(self, event, campaign_id=campaign_id)

    async def handle_session_created(self, event: Any) -> list[str]:
        return await handle_session_created(self, event)

    async def handle_participant_joined(self, event: Any) -> list[str]:
        return await handle_participant_joined(self, event)

    async def handle_character_created(self, event: Any) -> list[str]:
        return await handle_character_created(self, event)

    async def handle_token_placed(self, event: Any, campaign_id: str | None = None) -> list[str]:
        return await handle_token_placed(self, event, campaign_id=campaign_id)


__all__ = [
    "SyncResult",
    "ZitadelSpiceDBSyncService",
]
