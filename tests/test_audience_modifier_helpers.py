"""Behaviour of the shared checks for approved audience modifiers (TASK-0843).

The consumers in game_session, board_state and character_sheet call these checks before they
apply their own effect. A refused modifier raises `AudienceModifierError`, which dead-letters
the stream message (ADR-0015).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.audience_modifiers import (
    AudienceModifierError,
    approved_modifier,
    integer_parameter,
    parameter,
    require_same_campaign,
    text_parameter,
)


def _event(**overrides: Any) -> AudienceModifierApproved:
    fields: dict[str, Any] = {
        "proposal_id": uuid4(),
        "poll_id": uuid4(),
        "campaign_id": uuid4(),
        "session_id": uuid4(),
        "approved_by": "dm",
        "approved": True,
        "modifier_type": "weather_change",
        "parameters": {"weather": "rain", "x": 3},
    }
    fields.update(overrides)
    return AudienceModifierApproved(**fields)


def test_approved_modifier_returns_the_event_for_its_type() -> None:
    event = _event()

    assert approved_modifier(event, "weather_change") is event


def test_approved_modifier_ignores_a_rejected_proposal() -> None:
    assert approved_modifier(_event(approved=False), "weather_change") is None


def test_approved_modifier_ignores_another_modifier_type() -> None:
    assert approved_modifier(_event(modifier_type="hazard_spawn"), "weather_change") is None


def test_approved_modifier_ignores_another_event() -> None:
    assert approved_modifier("not an audience event", "weather_change") is None


def test_text_parameter_returns_the_value() -> None:
    assert text_parameter(_event(), "weather") == "rain"


@pytest.mark.parametrize(
    "parameters",
    [{}, {"weather": None}, {"weather": "   "}, {"weather": 5}],
    ids=["missing", "none", "blank", "not-text"],
)
def test_text_parameter_refuses_a_missing_blank_or_non_text_value(parameters: dict) -> None:
    with pytest.raises(AudienceModifierError, match="weather"):
        text_parameter(_event(parameters=parameters), "weather")


def test_parameter_returns_any_present_value() -> None:
    assert parameter(_event(parameters={"character_id": "abc"}), "character_id") == "abc"


def test_parameter_refuses_a_missing_value() -> None:
    with pytest.raises(AudienceModifierError, match="character_id"):
        parameter(_event(parameters={}), "character_id")


def test_integer_parameter_returns_an_integer() -> None:
    assert integer_parameter(_event(), "x") == 3


@pytest.mark.parametrize(
    "parameters", [{}, {"x": True}, {"x": "3"}], ids=["missing", "bool", "text"]
)
def test_integer_parameter_refuses_a_missing_bool_or_text_value(parameters: dict) -> None:
    with pytest.raises(AudienceModifierError, match="'x'"):
        integer_parameter(_event(parameters=parameters), "x")


def test_require_same_campaign_accepts_the_same_campaign_as_text_or_uuid() -> None:
    campaign_id = uuid4()
    event = _event(campaign_id=campaign_id)

    require_same_campaign(event, str(campaign_id), "session abc")


def test_require_same_campaign_refuses_another_campaign() -> None:
    event = _event()

    with pytest.raises(AudienceModifierError, match="belongs to campaign"):
        require_same_campaign(event, str(uuid4()), "session abc")
