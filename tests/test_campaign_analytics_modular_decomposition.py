"""Tests verifying modular decomposition and backward compatibility of campaign_analytics worker and event handlers.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from campaign_analytics import (
    AnalyticsEventDispatcher,
    CampaignAnalyticsWorker,
    handle_domain_event,
)
from campaign_analytics.event_handlers import (
    get_event_attr,
    is_event_type,
)
from campaign_analytics.storage import CampaignAnalyticsStorage
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


def test_modular_file_length_limits() -> None:
    """Verify both worker.py and event_handlers.py strictly comply with line length budgets."""
    pkg_dir = (
        Path(__file__).resolve().parent.parent
        / "services"
        / "campaign_analytics"
        / "src"
        / "campaign_analytics"
    )
    worker_file = pkg_dir / "worker.py"
    handlers_file = pkg_dir / "event_handlers.py"

    assert worker_file.exists()
    assert handlers_file.exists()

    worker_lines = len(worker_file.read_text().splitlines())
    handlers_lines = len(handlers_file.read_text().splitlines())

    assert worker_lines < 180, f"worker.py has {worker_lines} lines, exceeding 180 target"
    assert handlers_lines < 220, (
        f"event_handlers.py has {handlers_lines} lines, exceeding 220 target"
    )


def test_worker_backward_compatible_properties() -> None:
    """Verify CampaignAnalyticsWorker maintains backward-compatible tracking properties."""
    storage = CampaignAnalyticsStorage()
    worker = CampaignAnalyticsWorker(storage=storage)

    assert isinstance(worker.token_positions, dict)
    assert isinstance(worker.token_names, dict)
    assert isinstance(worker.active_combatants, dict)
    assert isinstance(worker.active_encounters, dict)

    # Verify setter mutability forwards to dispatcher
    worker.token_positions["tok_1"] = (5, 10)
    worker.token_names["tok_1"] = "Fighter"
    worker.active_combatants["sess_1"] = "tok_1"
    worker.active_encounters["sess_1"] = "enc_boss"

    assert worker.dispatcher.token_positions["tok_1"] == (5, 10)
    assert worker.dispatcher.token_names["tok_1"] == "Fighter"
    assert worker.dispatcher.active_combatants["sess_1"] == "tok_1"
    assert worker.dispatcher.active_encounters["sess_1"] == "enc_boss"

    # Backward-compatible helper methods
    event_dict = {"event_type": "SessionCreated", "title": "Test Title"}
    assert worker._get_attr(event_dict, "title") == "Test Title"
    assert worker._is_type(event_dict, ["SessionCreated"]) is True
    assert worker._is_type(event_dict, ["TokenMoved"]) is False


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
async def test_worker_process_event_delegates_to_dispatcher() -> None:
    """Verify worker.process_event public method dispatches seamlessly."""
    storage = CampaignAnalyticsStorage()
    worker = CampaignAnalyticsWorker(storage=storage)
    session_id, campaign_id = str(uuid4()), str(uuid4())

    await worker.process_event(
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
