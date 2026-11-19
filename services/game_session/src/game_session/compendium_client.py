"""HTTP client for rules_compendium monster stat blocks (TASK-0918).

game_session never imports the rules_compendium package. It reads
GET /api/v1/compendium/monsters/{name} and forwards the caller's `Authorization` with the
service credential, so that the caller's homebrew monsters of `campaign_id` resolve too.
rules_compendium has no batch read, so the reads run concurrently on one connection pool.

A monster that rules_compendium does not know gives no rating. Every other failure raises
CompendiumUnavailableError. Callers must surface the error. They must not substitute a
rating (ADR-0015 b).
"""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import ServiceUnavailableError
from runefoble_platform.service_client import ServiceClient, UpstreamError
from runefoble_platform.service_client.owner_routes import get_monster
from runefoble_platform.service_credential import expected_service_credential

RULES_COMPENDIUM_URL_ENV = "RUNEFOBLE_RULES_COMPENDIUM_URL"
RULES_COMPENDIUM_TIMEOUT_SECONDS = 5.0


class CompendiumUnavailableError(ServiceUnavailableError):
    """rules_compendium did not answer a stat block read."""


def _base_url() -> str:
    url = (PlatformSettings().rules_compendium_url or "").strip()
    if not url:
        raise CompendiumUnavailableError(f"{RULES_COMPENDIUM_URL_ENV} is not configured")
    return url.rstrip("/")


async def _read_rating(
    client: ServiceClient, name: str, params: dict[str, str] | None, authorization: str | None
) -> float | None:
    """Return the stat block rating of one monster, or None when the compendium has no such monster."""
    try:
        reply = await client.send(
            "GET",
            get_monster(name).path,
            authorization=authorization,
            timeout_s=RULES_COMPENDIUM_TIMEOUT_SECONDS,
            params=params,
        )
    except UpstreamError as exc:
        raise CompendiumUnavailableError(str(exc)) from exc
    if reply.status_code == 404:
        return None
    if reply.status_code != 200:
        raise CompendiumUnavailableError(
            f"rules_compendium returned HTTP {reply.status_code} for monster '{name}'"
        )
    try:
        rating = json.loads(reply.body).get("challenge_rating")
        return None if rating is None else float(rating)
    except (ValueError, TypeError, AttributeError) as exc:
        raise CompendiumUnavailableError(
            f"rules_compendium returned an invalid stat block for monster '{name}'"
        ) from exc


async def fetch_challenge_ratings(
    names: list[str], *, campaign_id: UUID | None, authorization: str | None
) -> list[float | None]:
    """Read the challenge rating of each monster name, in order. None marks an unknown monster.

    `campaign_id` adds the homebrew monsters of that campaign that the caller may view.
    Raise CompendiumUnavailableError when rules_compendium is unconfigured or fails.
    """
    if not names:
        return []
    params = {"campaign_id": str(campaign_id)} if campaign_id is not None else None
    client = ServiceClient("rules_compendium", _base_url(), expected_service_credential())
    try:
        return list(
            await asyncio.gather(
                *(_read_rating(client, name.strip(), params, authorization) for name in names)
            )
        )
    finally:
        await client.aclose()


__all__ = [
    "RULES_COMPENDIUM_URL_ENV",
    "CompendiumUnavailableError",
    "fetch_challenge_ratings",
]
