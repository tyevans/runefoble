"""Tests verifying modular decomposition of campaign_analytics worker and event handlers.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from campaign_analytics.event_handlers import (
    AnalyticsEventDispatcher,
    get_event_attr,
    handle_domain_event,
    is_event_type,
)
from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker
from runefoble_events.events import (
    CharacterHealthChanged,
    CombatRoundAdvanced,
    DiceRolled,
    SessionCreated,
    TokenMoved,
    TokenPlaced,
)


def test_import_and_exports_facade() -> None:
    """Verify that campaign_analytics exposes worker and event dispatcher symbols."""
    assert CampaignAnalyticsWorker is not None
    assert AnalyticsEventDispatcher is not None
    assert callable(handle_domain_event)
    assert callable(get_event_attr)
    assert callable(is_event_type)


def test_worker_exposes_only_canonical_event_handling() -> None:
    """Verify the worker exposes handle_event and no alias for it."""
    assert callable(CampaignAnalyticsWorker.handle_event)
    assert not hasattr(CampaignAnalyticsWorker, "process_event")


@pytest.mark.asyncio
async def test_direct_event_dispatch_and_projections() -> None:
    """Verify AnalyticsEventDispatcher handles events and updates storage without Redis loop."""
    storage = CampaignAnalyticsStorage()
    dispatcher = AnalyticsEventDispatcher(storage=storage)

    campaign_id, session_id = str(uuid4()), str(uuid4())
    token_id = str(uuid4())

    # 1. Dispatch SessionCreated via handle_domain_event
    await handle_domain_event(
        SessionCreated(
            aggregate_id=session_id,
            campaign_id=campaign_id,
            session_id=session_id,
            title="The Obsidian Spire",
        ),
        storage=storage,
        dispatcher=dispatcher,
    )

    # 2. Dispatch TokenPlaced
    await dispatcher.dispatch(
        TokenPlaced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=token_id,
            name="Seoni Sorcerer",
            token_type="pc",
            x=5,
            y=10,
        )
    )
    assert dispatcher.token_positions[token_id] == (5, 10)
    assert dispatcher.token_names[token_id] == "Seoni Sorcerer"

    # 3. Dispatch TokenMoved
    await dispatcher.dispatch(
        TokenMoved(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=token_id,
            name="Seoni Sorcerer",
            from_x=5,
            from_y=10,
            to_x=8,
            to_y=12,
        )
    )
    assert dispatcher.token_positions[token_id] == (8, 12)

    # 4. Dispatch DiceRolled
    await dispatcher.dispatch(
        DiceRolled(
            aggregate_id=uuid4(),
            session_id=session_id,
            roller_id=token_id,
            roller_name="Seoni Sorcerer",
            formula="1d20+8",
            total=28,
            is_crit=True,
        )
    )

    # 5. Dispatch CombatRoundAdvanced and CharacterHealthChanged
    await dispatcher.dispatch(
        CombatRoundAdvanced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            round_number=1,
            active_combatant_id=token_id,
        )
    )
    await dispatcher.dispatch(
        CharacterHealthChanged(
            aggregate_id=token_id,
            session_id=session_id,
            campaign_id=campaign_id,
            delta=-15,
            current_hp=10,
            max_hp=25,
            source="fire",
        )
    )

    # Verify projections in storage
    timeline = await storage.get_timeline(campaign_id=campaign_id)
    assert len(timeline.milestones) >= 3

    mvp = await storage.get_mvp(campaign_id=campaign_id)
    assert len(mvp.combatants) >= 1
    combatant = mvp.combatants[0]
    assert combatant.combatant_id == token_id
    assert combatant.critical_hits == 1
    assert combatant.damage_taken == 15
    assert combatant.turns_taken == 1

    heatmap = await storage.get_heatmap(campaign_id=campaign_id, cell_size=5)
    assert heatmap.total_points >= 3


@pytest.mark.asyncio
async def test_worker_handle_event_delegates_to_dispatcher() -> None:
    """Verify worker.handle_event dispatches a domain event into storage."""
    storage = CampaignAnalyticsStorage()
    worker = CampaignAnalyticsWorker(storage=storage)
    session_id, campaign_id = str(uuid4()), str(uuid4())

    await worker.handle_event(
        SessionCreated(
            aggregate_id=session_id,
            campaign_id=campaign_id,
            session_id=session_id,
            title="Tomb of Horrors",
        )
    )
    timeline = await storage.get_timeline(campaign_id=campaign_id)
    assert len(timeline.milestones) == 1
    assert timeline.milestones[0].type == "session_start"
    assert "Tomb of Horrors" in timeline.milestones[0].title
