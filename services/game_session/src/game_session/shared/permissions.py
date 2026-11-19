"""SpiceDB permission helpers that two or more game session domains call (ADR-0021 D2).

Governed by ADR-0001 (Zanzibar Fine-Grained Authorization) and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any

from runefoble_auth.permissions import check_subject


async def check_establishment_play_permission(
    spicedb: Any, establishment_id: str, user_id: str
) -> bool:
    """Return True when the user may play minigames at or patronize an establishment."""
    for p in ("play", "view", "manage"):
        if await check_subject(spicedb, "establishment", establishment_id, p, user_id):
            return True
    return False


__all__ = ["check_establishment_play_permission"]
