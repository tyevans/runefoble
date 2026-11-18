"""Campaign titles for character responses, read from the owning service (ADR-0007).

game_session owns campaigns. The gateway asks it for the title with the caller's token.
When the owner refuses the caller (4xx), the title is withheld (None). An unreachable or
failing owner raises the usual upstream error, so the gap is never hidden.
"""

from __future__ import annotations

from fastapi import Request
from gateway_api.proxy import forward_json
from gateway_api.upstream_errors import UpstreamRejectedError


async def campaign_titles(request: Request, campaign_ids: set[str]) -> dict[str, str | None]:
    """Return {campaign id: title}. A campaign the caller cannot view maps to None."""
    titles: dict[str, str | None] = {}
    for campaign_id in sorted(campaign_ids):
        try:
            body = await forward_json(
                request,
                service="game_session",
                method="GET",
                path=f"/api/v1/campaigns/{campaign_id}",
            )
        except UpstreamRejectedError:
            titles[campaign_id] = None
        else:
            titles[campaign_id] = body["title"]
    return titles
