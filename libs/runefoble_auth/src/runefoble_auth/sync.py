"""Zitadel OIDC and SpiceDB Zanzibar relationship synchronization service.

Automates relationship tuple provisioning from authenticated Zitadel user identities,
campaign memberships, character aggregates, and domain events into SpiceDB Zanzibar schema.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from runefoble_auth.spicedb import MockSpiceDBClient, Relationship, SpiceDBClient
from runefoble_auth.zitadel import AuthenticatedUser, ZitadelAuthService

logger = logging.getLogger(__name__)


class SyncResult(BaseModel):
    """Result summary of a synchronization operation."""

    status: str = "success"
    synced_tuples: list[str] = Field(default_factory=list)
    revoked_tuples: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ZitadelSpiceDBSyncService:
    """Translates identity events and user claims into Zanzibar relationship tuples."""

    def __init__(
        self,
        spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None,
        zitadel_auth: ZitadelAuthService | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 0.05,
    ) -> None:
        self.spicedb = spicedb_client if spicedb_client is not None else SpiceDBClient()
        self.zitadel = zitadel_auth if zitadel_auth is not None else ZitadelAuthService()
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    async def _execute_with_retry(self, coro_func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute SpiceDB operation with exponential backoff on transient errors."""
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await coro_func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "SpiceDB sync operation failed (attempt %d/%d): %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))
        if last_exc:
            raise last_exc

    async def _write_tuple(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> str:
        """Write a relationship tuple idempotently with retry."""
        await self._execute_with_retry(
            self.spicedb.write_relationship,
            resource_type=resource_type,
            resource_id=resource_id,
            relation=relation,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        return f"{resource_type}:{resource_id}#{relation}@{subject_type}:{subject_id}"

    async def _delete_tuple(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> str:
        """Delete a relationship tuple idempotently with retry."""
        await self._execute_with_retry(
            self.spicedb.delete_relationship,
            resource_type=resource_type,
            resource_id=resource_id,
            relation=relation,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        return f"{resource_type}:{resource_id}#{relation}@{subject_type}:{subject_id}"

    async def sync_user_claims(
        self,
        user_or_claims: AuthenticatedUser | dict[str, Any] | str,
        campaign_id: str | None = None,
    ) -> list[str]:
        """Translate Zitadel token or user claims into SpiceDB relationships."""
        if isinstance(user_or_claims, str):
            user = self.zitadel.decode_token(user_or_claims)
        elif isinstance(user_or_claims, AuthenticatedUser):
            user = user_or_claims
        elif isinstance(user_or_claims, dict):
            token = user_or_claims.get("token")
            if token:
                user = self.zitadel.decode_token(token)
            else:
                user = AuthenticatedUser(
                    user_id=str(user_or_claims.get("user_id") or user_or_claims.get("sub", "anon")),
                    username=str(user_or_claims.get("username") or "User"),
                    email=user_or_claims.get("email"),
                    roles=user_or_claims.get("roles", []),
                    is_admin=bool(user_or_claims.get("is_admin", False)),
                )
        else:
            raise ValueError(f"Unsupported user_or_claims type: {type(user_or_claims)}")

        synced: list[str] = []
        user_id = user.user_id

        # If campaign_id provided, sync roles
        if campaign_id:
            roles = set(user.roles)
            if user.is_admin:
                roles.add("gm")

            for role in roles:
                normalized = role.lower()
                if normalized in ("gm", "dm", "dungeon_master"):
                    synced.append(
                        await self._write_tuple("campaign", campaign_id, "gm", "user", user_id)
                    )
                    synced.append(
                        await self._write_tuple(
                            "campaign", campaign_id, "dungeon_master", "user", user_id
                        )
                    )
                elif normalized in ("player", "spectator", "owner"):
                    synced.append(
                        await self._write_tuple(
                            "campaign", campaign_id, normalized, "user", user_id
                        )
                    )

        return synced

    async def sync_membership(
        self,
        campaign_id: str,
        user_id: str,
        role: Literal["gm", "dungeon_master", "player", "spectator", "owner"] | str,
        session_id: str | None = None,
        action: Literal["grant", "revoke"] = "grant",
    ) -> list[str]:
        """Grant or revoke campaign or session roles for a given user."""
        normalized_role = role.lower()
        roles_to_modify: list[str] = []

        if normalized_role in ("gm", "dungeon_master", "dm"):
            roles_to_modify = ["gm", "dungeon_master"]
        elif normalized_role in ("player", "spectator", "owner"):
            roles_to_modify = [normalized_role]
        else:
            roles_to_modify = [normalized_role]

        modified_tuples: list[str] = []
        for r in roles_to_modify:
            if action == "grant":
                t = await self._write_tuple("campaign", campaign_id, r, "user", user_id)
                modified_tuples.append(t)
            elif action == "revoke":
                t = await self._delete_tuple("campaign", campaign_id, r, "user", user_id)
                modified_tuples.append(t)
            else:
                raise ValueError(f"Unsupported action: {action}")

        # If session_id provided, bind session to campaign
        if session_id and action == "grant":
            modified_tuples.extend(await self.sync_session_campaign(session_id, campaign_id))

        return modified_tuples

    async def sync_character_ownership(
        self,
        character_id: str | UUID,
        user_id: str,
        campaign_id: str | None = None,
    ) -> list[str]:
        """Bind character aggregate to owning user and parent campaign."""
        char_id_str = str(character_id)
        synced: list[str] = []

        # character:<id>#owner@user:<user_id>
        synced.append(await self._write_tuple("character", char_id_str, "owner", "user", user_id))

        # character:<id>#campaign@campaign:<id>
        if campaign_id:
            synced.append(
                await self._write_tuple(
                    "character", char_id_str, "campaign", "campaign", campaign_id
                )
            )

        return synced

    async def sync_session_campaign(
        self,
        session_id: str | UUID,
        campaign_id: str,
    ) -> list[str]:
        """Bind session to parent campaign in Zanzibar schema."""
        sess_id_str = str(session_id)
        synced: list[str] = []
        synced.append(
            await self._write_tuple("session", sess_id_str, "campaign", "campaign", campaign_id)
        )
        synced.append(
            await self._write_tuple(
                "game_session", sess_id_str, "campaign", "campaign", campaign_id
            )
        )
        return synced

    async def sync_board_token(
        self,
        token_id: str,
        character_id: str | UUID | None = None,
        campaign_id: str | None = None,
    ) -> list[str]:
        """Bind board token to character aggregate and campaign grid."""
        synced: list[str] = []
        if character_id:
            synced.append(
                await self._write_tuple(
                    "board_token", token_id, "character", "character", str(character_id)
                )
            )
        if campaign_id:
            synced.append(
                await self._write_tuple(
                    "board_token", token_id, "campaign", "campaign", campaign_id
                )
            )
        return synced

    async def batch_write_relationships(
        self,
        relationships: list[tuple[str, str, str, str, str] | Relationship],
    ) -> list[str]:
        """Batch write relationships idempotently."""
        synced: list[str] = []
        for item in relationships:
            if isinstance(item, Relationship):
                res_type, res_id, rel, s_type, s_id = (
                    item.resource_type,
                    item.resource_id,
                    item.relation,
                    item.subject_type,
                    item.subject_id,
                )
            else:
                res_type, res_id, rel, s_type, s_id = item
            key = await self._write_tuple(res_type, res_id, rel, s_type, s_id)
            synced.append(key)
        return synced

    async def reconcile_relationships(
        self,
        expected_tuples: list[tuple[str, str, str, str, str] | Relationship],
    ) -> dict[str, Any]:
        """Reconcile expected Zanzibar relationships against current state."""
        existing = await self.spicedb.read_relationships()
        existing_keys = {r.to_tuple_key() for r in existing}

        added: list[str] = []
        for item in expected_tuples:
            rel = item if isinstance(item, Relationship) else Relationship(*item)
            key = rel.to_tuple_key()
            if key not in existing_keys:
                await self._write_tuple(
                    rel.resource_type,
                    rel.resource_id,
                    rel.relation,
                    rel.subject_type,
                    rel.subject_id,
                )
                added.append(key)

        return {
            "reconciled": True,
            "total_expected": len(expected_tuples),
            "added_count": len(added),
            "added_tuples": added,
        }

    async def check_health(self) -> dict[str, Any]:
        """Report synchronization health and SpiceDB connectivity."""
        try:
            # Check basic read
            await self.spicedb.read_relationships()
            backend = (
                "mock"
                if isinstance(self.spicedb, MockSpiceDBClient)
                and not getattr(self.spicedb, "_grpc_client", None)
                else "grpc"
            )
            return {
                "status": "healthy",
                "spicedb_connected": True,
                "sync_service": "operational",
                "backend": backend,
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "spicedb_connected": False,
                "error": str(exc),
            }

    # -----------------------------------------------------------------------
    # Domain Event Ingestion Handlers
    # -----------------------------------------------------------------------

    async def handle_session_created(self, event: Any) -> list[str]:
        """Handle SessionCreated domain event to configure DM and session binding."""
        campaign_id = (
            getattr(event, "campaign_id", None)
            or getattr(event, "session_id", None)
            or str(getattr(event, "aggregate_id", ""))
        )
        dm_id = getattr(event, "dm_id", None) or getattr(event, "created_by", "system")
        session_id = getattr(event, "session_id", None) or str(
            getattr(event, "aggregate_id", campaign_id)
        )

        synced: list[str] = []
        if campaign_id and dm_id:
            synced.extend(await self.sync_membership(campaign_id, dm_id, "gm"))
        if session_id and campaign_id:
            synced.extend(await self.sync_session_campaign(session_id, campaign_id))
        return synced

    async def handle_participant_joined(self, event: Any) -> list[str]:
        """Handle ParticipantJoined or PlayerJoinedSession domain events."""
        campaign_id = (
            getattr(event, "campaign_id", None)
            or getattr(event, "session_id", None)
            or str(getattr(event, "aggregate_id", ""))
        )
        user_id = getattr(event, "user_id", None) or getattr(event, "player_id", None)
        role = getattr(event, "role", "player")

        synced: list[str] = []
        if campaign_id and user_id:
            synced.extend(await self.sync_membership(campaign_id, user_id, role))

        # If a character_id is included, also ensure ownership
        char_id = getattr(event, "character_id", None)
        if char_id and user_id:
            synced.extend(await self.sync_character_ownership(char_id, user_id, campaign_id))

        return synced

    async def handle_character_created(self, event: Any) -> list[str]:
        """Handle CharacterCreated domain event to establish character ownership."""
        char_id = getattr(event, "character_id", None) or str(getattr(event, "aggregate_id", ""))
        player_id = getattr(event, "player_id", None)
        campaign_id = getattr(event, "campaign_id", None)

        synced: list[str] = []
        if char_id and player_id:
            synced.extend(await self.sync_character_ownership(char_id, player_id, campaign_id))
        return synced

    async def handle_token_placed(self, event: Any, campaign_id: str | None = None) -> list[str]:
        """Handle TokenPlaced domain event to establish token spatial permissions."""
        token_id = getattr(event, "token_id", None) or str(getattr(event, "aggregate_id", ""))
        character_id = getattr(event, "character_id", None)
        camp_id = getattr(event, "campaign_id", None) or campaign_id

        return await self.sync_board_token(token_id, character_id, camp_id)
