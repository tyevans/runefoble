"""The owning bounded contexts that gateways call, and the settings field of each base URL.

Both gateways read this one map. A gateway builds one `ServiceClient` for each service
whose base URL is set. The service name is used in logs and in error bodies.
"""

from __future__ import annotations

from collections.abc import Mapping

# Service name -> PlatformSettings field (and GatewayMcpSettings field) with its base URL.
OWNER_URL_FIELDS: Mapping[str, str] = {
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
