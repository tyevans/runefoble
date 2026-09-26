"""Domain Event listener subscribing to Redis Streams for SpiceDB Zanzibar synchronization."""

from __future__ import annotations

import logging
from typing import Any

from runefoble_auth.sync import ZitadelSpiceDBSyncService

logger = logging.getLogger(__name__)


class SpiceDBEventListener:
    """Subscribes to domain events and coordinates relationship tuple provisioning."""

    def __init__(self, sync_service: ZitadelSpiceDBSyncService | None = None) -> None:
        self.sync_service = (
            sync_service if sync_service is not None else ZitadelSpiceDBSyncService()
        )

    async def on_session_created(self, event: Any) -> list[str]:
        """React to SessionCreated to provision DM and session-campaign relationships."""
        try:
            synced = await self.sync_service.handle_session_created(event)
            logger.info("Synchronized SessionCreated event: %s", synced)
            return synced
        except Exception as exc:
            logger.error("Failed to sync SessionCreated: %s", exc)
            return []

    async def on_participant_joined(self, event: Any) -> list[str]:
        """React to ParticipantJoined or PlayerJoinedSession to provision role tuples."""
        try:
            synced = await self.sync_service.handle_participant_joined(event)
            logger.info("Synchronized ParticipantJoined event: %s", synced)
            return synced
        except Exception as exc:
            logger.error("Failed to sync ParticipantJoined: %s", exc)
            return []

    async def on_character_created(self, event: Any) -> list[str]:
        """React to CharacterCreated to provision character ownership tuples."""
        try:
            synced = await self.sync_service.handle_character_created(event)
            logger.info("Synchronized CharacterCreated event: %s", synced)
            return synced
        except Exception as exc:
            logger.error("Failed to sync CharacterCreated: %s", exc)
            return []

    async def on_token_placed(self, event: Any, campaign_id: str | None = None) -> list[str]:
        """React to TokenPlaced to provision token spatial and ownership bindings."""
        try:
            synced = await self.sync_service.handle_token_placed(event, campaign_id=campaign_id)
            logger.info("Synchronized TokenPlaced event: %s", synced)
            return synced
        except Exception as exc:
            logger.error("Failed to sync TokenPlaced: %s", exc)
            return []

    def register_bus_handlers(self, event_bus: Any) -> None:
        """Register listeners with an EventBus or platform bus instance."""
        if hasattr(event_bus, "subscribe"):
            event_bus.subscribe("SessionCreated", self.on_session_created)
            event_bus.subscribe("ParticipantJoined", self.on_participant_joined)
            event_bus.subscribe("PlayerJoinedSession", self.on_participant_joined)
            event_bus.subscribe("CharacterCreated", self.on_character_created)
            event_bus.subscribe("TokenPlaced", self.on_token_placed)
            logger.info("Registered SpiceDB Zanzibar event listeners on EventBus.")
