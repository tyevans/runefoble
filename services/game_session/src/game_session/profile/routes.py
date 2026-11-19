"""Owner routes for the caller's profile under /api/v1/profile (TASK-0742).

The gateway forwards these requests with the caller's bearer token. This service verifies
that token itself (ADR-0015 c). The profile is event-sourced state keyed by the subject.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from game_session.profile.aggregate import UserProfileAggregate
from game_session.profile.repository import get_profile_repository, load_profile
from game_session.profile.schemas import ProfileResponse, UpdateProfileRequest
from game_session.profile.service import profile_view
from game_session.shared.identity import CallerPrincipal
from runefoble_platform.aggregate_loading import save_or_conflict
from runefoble_platform.event_sourcing import AggregateRepository

router = APIRouter(tags=["User Profile"])

ProfileRepo = Annotated[AggregateRepository[UserProfileAggregate], Depends(get_profile_repository)]


@router.get("/api/v1/profile", response_model=ProfileResponse)
async def get_profile(principal: CallerPrincipal, repo: ProfileRepo) -> ProfileResponse:
    """Read the caller's profile. Unedited fields show the token defaults."""
    aggregate = await load_profile(repo, principal.user_id)
    return profile_view(principal, aggregate.state)


@router.patch("/api/v1/profile", response_model=ProfileResponse)
async def update_profile(
    req: UpdateProfileRequest, principal: CallerPrincipal, repo: ProfileRepo
) -> ProfileResponse:
    """Edit the caller's profile. Only the fields sent are changed."""
    aggregate = await load_profile(repo, principal.user_id)
    aggregate.update(principal.user_id, req.changes())
    await save_or_conflict(
        repo,
        aggregate,
        lambda: HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The profile changed while this request ran. Retry.",
        ),
    )
    return profile_view(principal, aggregate.state)
