"""HTTP client for the stronghold treasury debit in game_session (TASK-0795).

campaign_lore never reads the Stronghold aggregate. It calls the public route
`POST /api/v1/campaigns/{campaign_id}/stronghold/treasury/contribute`. The caller's verified
bearer goes on the call, so game_session checks `stronghold.manage` for that user. The
service credential goes on every call (ADR-0015 e). Upstream failures raise UpstreamError.
Callers must surface them. They must not substitute a value (ADR-0015 b).
"""

from __future__ import annotations

import json

from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import ServiceUnavailableError
from runefoble_platform.service_client import ServiceClient, UpstreamError, UpstreamReply
from runefoble_platform.service_credential import expected_service_credential

GAME_SESSION_URL_ENV = "RUNEFOBLE_GAME_SESSION_URL"
GAME_SESSION_TIMEOUT_SECONDS = 5.0
CONTRIBUTE_PATH = "/api/v1/campaigns/{campaign_id}/stronghold/treasury/contribute"


def _base_url() -> str:
    url = (PlatformSettings().game_session_url or "").strip()
    if not url:
        raise ServiceUnavailableError(f"{GAME_SESSION_URL_ENV} is not configured")
    return url.rstrip("/")


async def debit_treasury_for_outpost(
    campaign_id: str, *, gold: int, destination_outpost_id: str, authorization: str
) -> UpstreamReply:
    """Ask game_session to debit the stronghold treasury. Return its reply unchanged.

    Raise ServiceUnavailableError when the URL is unset. Raise UpstreamError when game_session
    is unreachable or answers 5xx.
    """
    client = ServiceClient("game_session", _base_url(), expected_service_credential())
    try:
        return await client.send(
            "POST",
            CONTRIBUTE_PATH.format(campaign_id=campaign_id),
            authorization=authorization,
            timeout_s=GAME_SESSION_TIMEOUT_SECONDS,
            json={"gold": gold, "destination_outpost_id": destination_outpost_id},
        )
    except UpstreamError as exc:
        raise ServiceUnavailableError(f"game_session did not confirm the debit: {exc}") from exc
    finally:
        await client.aclose()


def upstream_detail(body: bytes) -> str:
    """Return the `detail` text of a game_session error body, or the raw body text."""
    try:
        payload = json.loads(body)
    except ValueError:
        return body.decode(errors="replace")
    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])
    return body.decode(errors="replace")


__all__ = [
    "GAME_SESSION_URL_ENV",
    "debit_treasury_for_outpost",
    "upstream_detail",
]
