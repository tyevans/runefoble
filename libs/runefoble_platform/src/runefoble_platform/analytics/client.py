"""OpenPanel async HTTP client with automated privacy scrubbing."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from runefoble_platform.analytics.privacy import anonymize_profile_id, sanitize_properties
from runefoble_platform.config import PlatformSettings

logger = logging.getLogger(__name__)


class OpenPanelClient:
    """Privacy-preserving OpenPanel client supporting non-blocking HTTP dispatch and mock recording."""

    def __init__(
        self,
        endpoint: str | None = None,
        client_id: str | None = None,
        salt: str = "runefoble_privacy_salt",
        mock_mode: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = PlatformSettings()
        raw_endpoint = endpoint or settings.openpanel_endpoint
        self.endpoint = raw_endpoint.rstrip("/") if raw_endpoint else "http://localhost:3000/api"
        self.client_id = client_id or settings.openpanel_client_id
        self.salt = salt
        self.mock_mode = mock_mode
        self._http_client = http_client
        self.recorded_events: list[dict[str, Any]] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=3.0)
        return self._http_client

    async def track(
        self,
        event_name: str,
        properties: dict[str, Any] | None = None,
        profile_id: str | UUID | None = None,
    ) -> dict[str, Any]:
        """Record an anonymized event and dispatch asynchronously to OpenPanel."""
        anon_profile = anonymize_profile_id(profile_id, salt=self.salt)
        clean_props = sanitize_properties(properties)

        payload: dict[str, Any] = {
            "event": event_name,
            "name": event_name,
            "properties": clean_props,
        }
        if anon_profile:
            payload["profile_id"] = anon_profile
        if self.client_id:
            payload["client_id"] = self.client_id

        self.recorded_events.append(payload)

        if not self.mock_mode and self.endpoint:
            url = f"{self.endpoint}/event"
            headers = {"Content-Type": "application/json"}
            if self.client_id:
                headers["openpanel-client-id"] = self.client_id
            try:
                client = await self._get_client()
                await client.post(url, json=payload, headers=headers)
            except Exception as exc:
                logger.warning("OpenPanel async dispatch failed for '%s': %s", event_name, exc)

        return payload

    async def identify(
        self,
        profile_id: str | UUID,
        traits: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an anonymized profile identifier with privacy-sanitized traits."""
        anon_profile = anonymize_profile_id(profile_id, salt=self.salt)
        clean_traits = sanitize_properties(traits)
        payload: dict[str, Any] = {
            "profile_id": anon_profile,
            "traits": clean_traits,
        }
        if self.client_id:
            payload["client_id"] = self.client_id

        self.recorded_events.append(payload)

        if not self.mock_mode and self.endpoint:
            url = f"{self.endpoint}/profile"
            headers = {"Content-Type": "application/json"}
            if self.client_id:
                headers["openpanel-client-id"] = self.client_id
            try:
                client = await self._get_client()
                await client.post(url, json=payload, headers=headers)
            except Exception as exc:
                logger.warning("OpenPanel profile dispatch failed: %s", exc)

        return payload

    def clear(self) -> None:
        """Clear recorded events from memory buffer."""
        self.recorded_events.clear()

    async def close(self) -> None:
        """Close internal HTTP client session."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


__all__ = ["OpenPanelClient"]
