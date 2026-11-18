"""Profile use cases: read the caller's profile and apply the caller's edits.

The caller is always the verified token subject. No route accepts another user's ID.
"""

from __future__ import annotations

from game_session.profile.aggregate import UserProfileState
from game_session.profile.schemas import ProfileResponse
from runefoble_auth.principal import VerifiedPrincipal


def profile_view(principal: VerifiedPrincipal, state: UserProfileState) -> ProfileResponse:
    """Merge the stored edits over the token defaults. An unedited field uses its default."""
    return ProfileResponse(
        user_id=principal.user_id,
        username=principal.username,
        email=state.email if state.email is not None else principal.email,
        display_name=(state.display_name if state.display_name is not None else principal.username),
        avatar_url=state.avatar_url,
        bio=state.bio if state.bio is not None else "",
    )
