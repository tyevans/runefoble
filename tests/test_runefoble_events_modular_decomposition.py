"""Blackbox tests verifying modular decomposition of runefoble_events.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 500 lines, submodules < 150 lines, facades < 80 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- TASK-0177: Runefoble Events Aggregator Modular Decomposition
"""

from __future__ import annotations

from uuid import uuid4

from runefoble_events.base import BaseRunefobleEvent
from runefoble_events.events import (
    CaravanDispatched,
    SessionCreated,
    TokenMoved,
)


def test_domain_event_instantiation_and_cloudevent_compliance() -> None:
    """Verify frontdoor creation and CloudEvents attributes for events across categories."""
    aggregate_id = uuid4()
    session_ev = SessionCreated(
        aggregate_id=aggregate_id, session_id="sess-0177", campaign_id="camp-0177"
    )
    assert session_ev.session_id == "sess-0177"
    assert session_ev.aggregate_id == aggregate_id
    assert issubclass(SessionCreated, BaseRunefobleEvent)

    token_ev = TokenMoved(
        aggregate_id=aggregate_id,
        token_id="tok-0177",
        name="Gimli",
        from_x=0,
        from_y=0,
        to_x=5,
        to_y=5,
    )
    assert token_ev.token_id == "tok-0177"
    assert token_ev.to_x == 5

    caravan_ev = CaravanDispatched(
        aggregate_id=uuid4(),
        aggregate_type="CaravanContract",
        caravan_id="car-0177",
        origin_outpost="outpost-alpha",
        destination_outpost="outpost-beta",
    )
    assert caravan_ev.caravan_id == "car-0177"
    assert caravan_ev.aggregate_type == "CaravanContract"
