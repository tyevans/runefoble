"""Registry of the gateway's service clients, one per configured owning service.

The gateway builds this registry once in the FastAPI lifespan from `PlatformSettings`.
It closes every client on shutdown.
"""

from __future__ import annotations

from collections.abc import Mapping

from runefoble_platform.config import PlatformSettings
from runefoble_platform.service_client import ServiceClient, UpstreamUnavailableError
from runefoble_platform.service_credential import expected_service_credential

# Service name used in logs and error bodies -> PlatformSettings field with its base URL.
UPSTREAM_SETTINGS: Mapping[str, str] = {
    "game_session": "game_session_url",
    "board_state": "board_state_url",
    "the_watcher": "the_watcher_url",
    "character_sheet": "character_sheet_url",
    "campaign_lore": "campaign_lore_url",
    "campaign_analytics": "campaign_analytics_url",
    "soundscape": "soundscape_url",
    "rules_compendium": "rules_compendium_url",
    "asset_forge": "asset_forge_url",
    "voice_agent": "voice_agent_url",
    "audience_studio": "audience_studio_url",
}


class UpstreamRegistry:
    """Hold one ServiceClient per service whose base URL is configured."""

    def __init__(self, clients: Mapping[str, ServiceClient], health_probe_timeout_s: float) -> None:
        self._clients = dict(clients)
        # Seconds that each downstream health probe on /healthz may wait (TASK-0674).
        self.health_probe_timeout_s = health_probe_timeout_s

    @classmethod
    def from_settings(cls, settings: PlatformSettings) -> UpstreamRegistry:
        clients: dict[str, ServiceClient] = {}
        credential = expected_service_credential(settings)
        for service, field in UPSTREAM_SETTINGS.items():
            base_url = getattr(settings, field)
            if base_url:
                clients[service] = ServiceClient(service, base_url, credential)
        return cls(clients, settings.gateway_health_probe_timeout_s)

    def find(self, service: str) -> ServiceClient | None:
        """Return the client for a service, or None when no base URL is set."""
        return self._clients.get(service)

    def client(self, service: str) -> ServiceClient:
        """Return the client for a service. Raise UpstreamUnavailableError when no URL is set."""
        client = self.find(service)
        if client is None:
            raise UpstreamUnavailableError(service, "no base URL is configured")
        return client

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
