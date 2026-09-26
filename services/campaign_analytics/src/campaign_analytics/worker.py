"""Telemetry projection worker consuming Redis Streams domain events into PostgreSQL analytical tables.

Governed by:
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from eventsource.domain.event import DomainEvent
from pydantic import BaseModel
from runefoble_platform.consumer_group import RedisConsumerGroup

from campaign_analytics.storage import CampaignAnalyticsStorage

logger = logging.getLogger("runefoble.campaign_analytics.worker")


class CampaignAnalyticsWorker:
    """Asynchronous background worker translating Redis Streams events into analytical projections."""

    def __init__(
        self,
        storage: CampaignAnalyticsStorage,
        consumer_group: RedisConsumerGroup | None = None,
        streams: list[str] | str | None = None,
        group_name: str = "campaign_analytics_worker",
        consumer_name: str = "campaign_analytics_consumer_1",
        poll_interval_ms: int = 100,
    ) -> None:
        self.storage = storage
        self.consumer_group = consumer_group
        if streams is None:
            self.streams = [
                "runefoble.events.session",
                "runefoble.events.board",
                "runefoble.events.character",
                "runefoble.events.watcher",
            ]
        elif isinstance(streams, str):
            self.streams = [streams]
        else:
            self.streams = list(streams)

        self.group_name = group_name
        self.consumer_name = consumer_name
        self.poll_interval_ms = poll_interval_ms
        self.running: bool = False
        self._task: asyncio.Task[None] | None = None
        self.processed_count: int = 0

        # Ephemeral spatial tracking state
        self.token_positions: dict[str, tuple[int, int]] = {}
        self.token_names: dict[str, str] = {}
        self.active_combatants: dict[str, str] = {}
        self.active_encounters: dict[str, str] = {}

    async def setup_groups(self) -> None:
        """Ensure consumer groups exist across all monitored streams."""
        if not self.consumer_group:
            return
        for stream in self.streams:
            with contextlib.suppress(Exception):
                await self.consumer_group.create_group(
                    stream=stream,
                    group_name=self.group_name,
                    start_id="0",
                    make_stream=True,
                )

    def _get_attr(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            val = obj.get(key)
            if val is not None:
                return val
            data = obj.get("data")
            if isinstance(data, dict):
                val = data.get(key)
                if val is not None:
                    return val
            return default
        return getattr(obj, key, default)

    def _is_type(self, obj: Any, candidates: list[str]) -> bool:
        etype: str = ""
        if isinstance(obj, dict):
            etype = str(obj.get("event_type") or obj.get("type") or "")
            if not etype:
                data = obj.get("data")
                if isinstance(data, dict):
                    etype = str(data.get("event_type") or "")
        elif isinstance(obj, (DomainEvent, BaseModel)):
            etype = getattr(obj, "event_type", obj.__class__.__name__)
        if not etype:
            etype = obj.__class__.__name__

        return any(
            cand.lower() in etype.lower() or etype.lower().endswith(cand.lower())
            for cand in candidates
        )

    async def handle_event(self, event: Any) -> None:
        """Process a single domain event and update analytical read-models."""
        # Extract session_id and campaign_id
        raw_sess = self._get_attr(event, "session_id") or self._get_attr(event, "aggregate_id")
        session_id = str(raw_sess) if raw_sess else ""
        raw_camp = self._get_attr(event, "campaign_id") or self._get_attr(event, "campaign_id_str")
        campaign_id = str(raw_camp) if raw_camp else self.storage.resolve_campaign_id(session_id)

        # 1. SessionCreated / SessionStarted
        if self._is_type(event, ["SessionCreated", "runefoble.events.session.created"]):
            title = str(self._get_attr(event, "title", "Untitled Session"))
            cid = str(self._get_attr(event, "campaign_id", ""))
            if cid and session_id:
                self.storage.map_session(session_id, cid)
                campaign_id = cid
            await self.storage.record_milestone(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                milestone_type="session_start",
                title=f"Session Created: {title}",
                description=f"Campaign session '{title}' created.",
                metadata_dict={"title": title},
            )
            return

        if self._is_type(event, ["SessionStarted", "GameSessionStarted"]):
            await self.storage.record_milestone(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                milestone_type="session_start",
                title="Session Began",
                description="The party assembled and the session officially commenced.",
            )
            return

        # 2. SessionEnded
        if self._is_type(event, ["SessionEnded", "runefoble.events.session.ended"]):
            summary = str(self._get_attr(event, "summary", "Session concluded"))
            await self.storage.record_milestone(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                milestone_type="session_end",
                title="Session Concluded",
                description=summary,
                metadata_dict={"summary": summary},
            )
            return

        # 3. TokenPlaced / TokenMoved
        if self._is_type(event, ["TokenPlaced"]):
            tok_id = str(self._get_attr(event, "token_id", ""))
            name = str(self._get_attr(event, "name", "Token"))
            x = int(self._get_attr(event, "x", 0))
            y = int(self._get_attr(event, "y", 0))
            if tok_id:
                self.token_positions[tok_id] = (x, y)
                self.token_names[tok_id] = name
            await self.storage.record_spatial(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                token_id=tok_id,
                token_name=name,
                x=x,
                y=y,
                event_type="movement",
            )
            return

        if self._is_type(event, ["TokenMoved", "BoardMoveEvent"]):
            tok_id = str(self._get_attr(event, "token_id", ""))
            name = str(self._get_attr(event, "name", "Token"))
            to_x = int(self._get_attr(event, "to_x", 0))
            to_y = int(self._get_attr(event, "to_y", 0))
            if tok_id:
                self.token_positions[tok_id] = (to_x, to_y)
                self.token_names[tok_id] = name
            await self.storage.record_spatial(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                token_id=tok_id,
                token_name=name,
                x=to_x,
                y=to_y,
                event_type="movement",
            )
            return

        # 4. CharacterHealthChanged
        if self._is_type(event, ["CharacterHealthChanged"]):
            char_id = str(self._get_attr(event, "aggregate_id", ""))
            delta = int(self._get_attr(event, "delta", 0))
            curr_hp = int(self._get_attr(event, "current_hp", 0))
            actor = str(
                self._get_attr(event, "dealer_id")
                or self.active_combatants.get(session_id)
                or char_id
            )
            pos = self.token_positions.get(char_id, (0, 0))
            char_name = self.token_names.get(char_id, char_id)

            if delta < 0:
                dmg = abs(delta)
                # Attribute damage taken to character, and damage dealt to active combatant if distinct
                await self.storage.record_combatant_stat(
                    campaign_id=campaign_id or session_id,
                    session_id=session_id,
                    encounter_id=self.active_encounters.get(session_id, "default"),
                    combatant_id=char_id,
                    combatant_name=char_name,
                    damage_taken=dmg,
                )
                if actor and actor != char_id:
                    await self.storage.record_combatant_stat(
                        campaign_id=campaign_id or session_id,
                        session_id=session_id,
                        encounter_id=self.active_encounters.get(session_id, "default"),
                        combatant_id=actor,
                        combatant_name=self.token_names.get(actor, actor),
                        damage_dealt=dmg,
                    )
                # Spatial telemetry
                await self.storage.record_spatial(
                    campaign_id=campaign_id or session_id,
                    session_id=session_id,
                    token_id=char_id,
                    token_name=char_name,
                    x=pos[0],
                    y=pos[1],
                    event_type="damage",
                    damage=dmg,
                )
                # Knockout detection
                if curr_hp <= 0:
                    await self.storage.record_spatial(
                        campaign_id=campaign_id or session_id,
                        session_id=session_id,
                        token_id=char_id,
                        token_name=char_name,
                        x=pos[0],
                        y=pos[1],
                        event_type="knockout",
                    )
                    await self.storage.record_milestone(
                        campaign_id=campaign_id or session_id,
                        session_id=session_id,
                        milestone_type="character_knockout",
                        title=f"{char_name} Knocked Unconscious",
                        description=f"{char_name} took lethal damage and fell to 0 HP at coordinates ({pos[0]}, {pos[1]}).",
                        metadata_dict={"character_id": char_id, "coordinates": list(pos)},
                    )
            elif delta > 0:
                await self.storage.record_combatant_stat(
                    campaign_id=campaign_id or session_id,
                    session_id=session_id,
                    encounter_id=self.active_encounters.get(session_id, "default"),
                    combatant_id=actor,
                    combatant_name=self.token_names.get(actor, actor),
                    healing_provided=delta,
                )
            return

        # 5. DiceRolled
        if self._is_type(event, ["DiceRolled", "DiceRollEvent", "runefoble.events.dice.rolled"]):
            roller_id = str(self._get_attr(event, "roller_id", "roller"))
            roller_name = str(self._get_attr(event, "roller_name", roller_id))
            if roller_id and roller_name:
                self.token_names[roller_id] = roller_name
            formula = str(self._get_attr(event, "formula", "1d20"))
            total = int(self._get_attr(event, "total", 0))
            is_crit = bool(self._get_attr(event, "is_crit", False))
            is_fumble = bool(self._get_attr(event, "is_fumble", False))

            await self.storage.record_combatant_stat(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                encounter_id=self.active_encounters.get(session_id, "default"),
                combatant_id=roller_id,
                combatant_name=roller_name,
                critical_hits=1 if is_crit else 0,
                fumbles=1 if is_fumble else 0,
            )
            if is_crit:
                await self.storage.record_milestone(
                    campaign_id=campaign_id or session_id,
                    session_id=session_id,
                    milestone_type="critical_moment",
                    title=f"Critical Strike by {roller_name}!",
                    description=f"{roller_name} rolled a natural critical ({total}) on {formula}.",
                    metadata_dict={
                        "roller_id": roller_id,
                        "formula": formula,
                        "total": total,
                    },
                )
            return

        # 6. CombatRoundAdvanced
        if self._is_type(event, ["CombatRoundAdvanced"]):
            rnd = int(self._get_attr(event, "round_number", 1))
            active_id = str(self._get_attr(event, "active_combatant_id", ""))
            if active_id and session_id:
                self.active_combatants[session_id] = active_id
                await self.storage.record_combatant_stat(
                    campaign_id=campaign_id or session_id,
                    session_id=session_id,
                    encounter_id=self.active_encounters.get(session_id, "default"),
                    combatant_id=active_id,
                    combatant_name=self.token_names.get(active_id, active_id),
                    turns_taken=1,
                )
            await self.storage.record_milestone(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                milestone_type="combat_round",
                title=f"Combat Round {rnd}",
                description=f"Encounter advanced to round {rnd}.",
                metadata_dict={"round_number": rnd, "active_combatant_id": active_id},
            )
            return

        # 7. CombatEncounterStarted / EncounterSpawned
        if self._is_type(
            event,
            [
                "CombatEncounterStarted",
                "CombatStarted",
                "EncounterSpawned",
                "runefoble.events.encounter.spawned",
            ],
        ):
            enc_name = str(
                self._get_attr(event, "encounter_name") or self._get_attr(event, "name") or "Combat"
            )
            enc_id = str(self._get_attr(event, "encounter_id", "enc_1"))
            if session_id:
                self.active_encounters[session_id] = enc_id
            await self.storage.record_milestone(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                milestone_type="boss_encounter",
                title=f"Encounter Initiated: {enc_name}",
                description=f"Tactical encounter '{enc_name}' commenced.",
                metadata_dict={"encounter_id": enc_id, "name": enc_name},
            )
            return

        # 8. AbsenteeRecapGenerated
        if self._is_type(event, ["AbsenteeRecapGenerated", "runefoble.events.recap.generated"]):
            cname = str(self._get_attr(event, "character_name", "Adventurer"))
            narrative = str(self._get_attr(event, "narrative_summary", ""))
            await self.storage.record_milestone(
                campaign_id=campaign_id or session_id,
                session_id=session_id,
                milestone_type="recap",
                title=f"Chronicle Recap: {cname}",
                description=narrative or f"Session recap recorded for {cname}.",
                metadata_dict={"character_name": cname},
            )
            return

    async def process_once(self, count: int = 10, block_ms: int = 100) -> int:
        """Poll monitored streams once and apply projection events."""
        if not self.consumer_group:
            return 0
        total = 0
        for stream in self.streams:
            try:
                entries = await self.consumer_group.read_group(
                    stream=stream,
                    group_name=self.group_name,
                    consumer_name=self.consumer_name,
                    count=count,
                    block_ms=block_ms,
                )
            except Exception as e:
                logger.debug("read_group on %s: %s", stream, e)
                continue

            for msg_id, payload in entries:
                try:
                    await self.handle_event(payload)
                    await self.consumer_group.ack(stream, self.group_name, msg_id)
                    total += 1
                    self.processed_count += 1
                except Exception as e:
                    logger.warning("Error processing event %s: %s", msg_id, e)
                    await self.consumer_group.ack(stream, self.group_name, msg_id)
        return total

    async def start(self) -> None:
        """Start the background consumer loop."""
        if self.running:
            return
        self.running = True
        await self.setup_groups()

        async def _loop() -> None:
            while self.running:
                try:
                    await self.process_once(count=10, block_ms=self.poll_interval_ms)
                except Exception as e:
                    logger.error("Error in campaign analytics worker loop: %s", e)
                await asyncio.sleep(self.poll_interval_ms / 1000.0)

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        """Stop background worker."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
