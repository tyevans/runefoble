"""Shared checks for consumers of approved audience modifiers (TASK-0843).

Governed by ADR-0007 (each owner applies its own effect) and ADR-0015 (fail loud).
The consumers in game_session, board_state and character_sheet call these checks before they
apply their own effect. A refused modifier raises `AudienceModifierError`, so the stream
consumer routes the message to the dead-letter stream.
"""

from __future__ import annotations

from typing import Any

from runefoble_events.events import AudienceModifierApproved


class AudienceModifierError(RuntimeError):
    """Raised when an approved audience modifier cannot be applied."""


def refusal(modifier: AudienceModifierApproved, detail: str) -> AudienceModifierError:
    """Build the error for a modifier that a consumer refuses. `detail` completes the sentence."""
    return AudienceModifierError(
        f"Approved {modifier.modifier_type} modifier {modifier.proposal_id} {detail}"
    )


def approved_audience_modifier(event: Any) -> AudienceModifierApproved | None:
    """Return the event when the DM approved it, whatever its type. Otherwise None.

    A rejected proposal and a message that is not a modifier return None.
    """
    if not isinstance(event, AudienceModifierApproved):
        return None
    if event.approved is not True:
        return None
    return event


def approved_modifier(event: Any, modifier_type: str) -> AudienceModifierApproved | None:
    """Return the event when it is an approved modifier of `modifier_type`, otherwise None.

    A rejected proposal and a modifier of another type belong to other steps, so they return None.
    """
    modifier = approved_audience_modifier(event)
    if modifier is None or modifier.modifier_type != modifier_type:
        return None
    return modifier


def parameter(modifier: AudienceModifierApproved, name: str) -> Any:
    """Return a parameter that is present and not blank. Raises when it is missing."""
    value = modifier.parameters.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise refusal(modifier, f"has no '{name}' parameter.")
    return value


def text_parameter(modifier: AudienceModifierApproved, name: str) -> str:
    """Return a non-blank text parameter. Raises when it is missing, blank or not text."""
    value = parameter(modifier, name)
    if not isinstance(value, str):
        raise refusal(modifier, f"needs a text '{name}' parameter.")
    return value


def integer_parameter(modifier: AudienceModifierApproved, name: str) -> int:
    """Return an integer parameter. A boolean or a text value is refused."""
    value = modifier.parameters.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise refusal(modifier, f"needs an integer '{name}' parameter.")
    return value


def require_same_campaign(
    modifier: AudienceModifierApproved, owner_campaign_id: object, owner: str
) -> None:
    """Refuse the modifier when the owner belongs to another campaign.

    `owner` names the owning record in the message, for example "session <id>".
    """
    if str(owner_campaign_id) != str(modifier.campaign_id):
        raise refusal(
            modifier,
            f"belongs to campaign {modifier.campaign_id}, not to the campaign of {owner}.",
        )
