"""Persistent analytical storage engine for Campaign Analytics read-models.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind (PostgreSQL persistence)
- ADR-0011: eventsource-py Core Event Sourcing (Read-model projections)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from runefoble_platform.config import PlatformSettings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from campaign_analytics.models import (
    CampaignHeatmapResponse,
    CampaignMvpResponse,
    CampaignTimelineResponse,
    CombatantPerformance,
    HeatmapCell,
    MvpAward,
    TimelineMilestone,
)
from campaign_analytics.schema import (
    metadata,
    spatial_table,
    timeline_table,
)

logger = logging.getLogger("runefoble.campaign_analytics.storage")


class CampaignAnalyticsStorage:
    """Analytical read-model projection storage supporting PostgreSQL and in-memory fallback."""

    def __init__(
        self,
        engine: AsyncEngine | None = None,
        database_url: str | None = None,
    ) -> None:
        self.engine = engine
        self._db_url = database_url
        # In-memory stores for zero-latency queries and testing
        self.session_to_campaign: dict[str, str] = {}
        self.spatial_records: list[dict[str, Any]] = []
        self.combatants: dict[str, dict[str, Any]] = {}
        self.milestones: list[dict[str, Any]] = []

    @classmethod
    async def create(cls, settings: PlatformSettings | None = None) -> CampaignAnalyticsStorage:
        s = settings or PlatformSettings()
        db_url = str(s.database_url)
        engine: AsyncEngine | None = None
        if "postgresql" in db_url:
            try:
                engine = create_async_engine(db_url, pool_size=5, max_overflow=10)
                async with engine.begin() as conn:
                    await conn.run_sync(metadata.create_all)
                logger.info("Connected to PostgreSQL analytical database.")
            except Exception as e:
                logger.warning("PostgreSQL unreachable (%s). Using in-memory fallback.", e)
                engine = None
        return cls(engine=engine, database_url=db_url)

    def map_session(self, session_id: str, campaign_id: str) -> None:
        """Map session_id to campaign_id."""
        if session_id and campaign_id:
            self.session_to_campaign[str(session_id)] = str(campaign_id)

    def resolve_campaign_id(self, id_or_session: str) -> str:
        """Resolve a campaign_id, mapping from session_id if necessary."""
        return self.session_to_campaign.get(str(id_or_session), str(id_or_session))

    def _matches_campaign(self, rec_campaign: str, rec_session: str, query_id: str) -> bool:
        q = str(query_id)
        return (
            rec_campaign == q
            or rec_session == q
            or self.session_to_campaign.get(rec_session) == q
            or self.session_to_campaign.get(q) == rec_campaign
        )

    async def record_spatial(
        self,
        campaign_id: str,
        session_id: str,
        token_id: str,
        token_name: str,
        x: int,
        y: int,
        event_type: str = "movement",
        damage: int = 0,
        recorded_at: str | None = None,
    ) -> None:
        """Store spatial coordinate event."""
        now = recorded_at or datetime.now(UTC).isoformat()
        rec = {
            "id": str(uuid4()),
            "campaign_id": str(campaign_id),
            "session_id": str(session_id),
            "token_id": str(token_id),
            "token_name": token_name,
            "x": int(x),
            "y": int(y),
            "event_type": event_type,
            "damage": int(damage),
            "recorded_at": now,
        }
        self.spatial_records.append(rec)
        if self.engine:
            try:
                async with self.engine.begin() as conn:
                    await conn.execute(spatial_table.insert().values(rec))
            except Exception as e:
                logger.debug("Failed asyncpg write to spatial_table: %s", e)

    async def record_combatant_stat(
        self,
        campaign_id: str,
        session_id: str,
        encounter_id: str,
        combatant_id: str,
        combatant_name: str,
        damage_dealt: int = 0,
        damage_taken: int = 0,
        healing_provided: int = 0,
        critical_hits: int = 0,
        fumbles: int = 0,
        turns_taken: int = 0,
    ) -> None:
        """Update cumulative combatant performance metrics."""
        cid = str(combatant_id)
        key = f"{campaign_id}:{session_id}:{cid}"
        if key not in self.combatants:
            self.combatants[key] = {
                "id": str(uuid4()),
                "campaign_id": str(campaign_id),
                "session_id": str(session_id),
                "encounter_id": encounter_id or "default",
                "combatant_id": cid,
                "combatant_name": combatant_name,
                "damage_dealt": 0,
                "damage_taken": 0,
                "healing_provided": 0,
                "critical_hits": 0,
                "fumbles": 0,
                "turns_taken": 0,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        entry = self.combatants[key]
        if combatant_name:
            entry["combatant_name"] = combatant_name
        entry["damage_dealt"] += damage_dealt
        entry["damage_taken"] += damage_taken
        entry["healing_provided"] += healing_provided
        entry["critical_hits"] += critical_hits
        entry["fumbles"] += fumbles
        entry["turns_taken"] += turns_taken
        entry["updated_at"] = datetime.now(UTC).isoformat()

    async def record_milestone(
        self,
        campaign_id: str,
        session_id: str,
        milestone_type: str,
        title: str,
        description: str,
        timestamp: str | None = None,
        metadata_dict: dict[str, Any] | None = None,
    ) -> None:
        """Record a campaign milestone."""
        now = timestamp or datetime.now(UTC).isoformat()
        rec = {
            "id": str(uuid4()),
            "campaign_id": str(campaign_id),
            "session_id": str(session_id),
            "milestone_type": milestone_type,
            "title": title,
            "description": description,
            "timestamp": now,
            "metadata": metadata_dict or {},
        }
        self.milestones.append(rec)
        if self.engine:
            try:
                import json

                async with self.engine.begin() as conn:
                    await conn.execute(
                        timeline_table.insert().values(
                            id=rec["id"],
                            campaign_id=rec["campaign_id"],
                            session_id=rec["session_id"],
                            milestone_type=rec["milestone_type"],
                            title=rec["title"],
                            description=rec["description"],
                            timestamp=rec["timestamp"],
                            metadata_json=json.dumps(rec["metadata"]),
                        )
                    )
            except Exception as e:
                logger.debug("Failed asyncpg write to timeline_table: %s", e)

    async def get_heatmap(
        self,
        campaign_id: str,
        session_id: str | None = None,
        cell_size: int = 5,
        metric: str = "all",
    ) -> CampaignHeatmapResponse:
        """Query aggregated spatial coordinate hit/damage densities."""
        cell_size = max(1, cell_size)
        filtered = [
            r
            for r in self.spatial_records
            if self._matches_campaign(r["campaign_id"], r["session_id"], campaign_id)
            and (not session_id or r["session_id"] == session_id)
        ]
        if metric in ("damage", "hit"):
            filtered = [r for r in filtered if r["event_type"] in ("damage", "knockout")]
        elif metric == "movement":
            filtered = [r for r in filtered if r["event_type"] == "movement"]

        buckets: dict[tuple[int, int], dict[str, int]] = {}
        for r in filtered:
            bx = (r["x"] // cell_size) * cell_size
            by = (r["y"] // cell_size) * cell_size
            key = (bx, by)
            if key not in buckets:
                buckets[key] = {
                    "density": 0,
                    "movement_count": 0,
                    "damage_total": 0,
                    "hit_count": 0,
                    "knockout_count": 0,
                }
            cell = buckets[key]
            etype = r["event_type"]
            dmg = r["damage"]
            if etype == "movement":
                cell["movement_count"] += 1
                cell["density"] += 1
            elif etype == "damage":
                cell["damage_total"] += dmg
                cell["hit_count"] += 1
                cell["density"] += max(1, dmg // 5)
            elif etype == "knockout":
                cell["knockout_count"] += 1
                cell["density"] += 5

        cells: list[HeatmapCell] = []
        max_density = 0
        for (bx, by), data in sorted(buckets.items()):
            max_density = max(max_density, data["density"])
            cells.append(
                HeatmapCell(
                    x=bx,
                    y=by,
                    density=data["density"],
                    movement_count=data["movement_count"],
                    damage_total=data["damage_total"],
                    hit_count=data["hit_count"],
                    knockout_count=data["knockout_count"],
                )
            )

        return CampaignHeatmapResponse(
            campaign_id=campaign_id,
            session_id=session_id,
            cell_size=cell_size,
            metric=metric,
            total_points=len(filtered),
            max_density=max_density,
            cells=cells,
        )

    async def get_mvp(
        self,
        campaign_id: str,
        session_id: str | None = None,
        encounter_id: str | None = None,
    ) -> CampaignMvpResponse:
        """Query combatant MVP rankings and awards."""
        filtered = [
            v
            for v in self.combatants.values()
            if self._matches_campaign(v["campaign_id"], v["session_id"], campaign_id)
            and (not session_id or v["session_id"] == session_id)
            and (not encounter_id or v.get("encounter_id") == encounter_id)
        ]
        combatants: list[CombatantPerformance] = []
        for v in filtered:
            score = (
                v["damage_dealt"] * 1.0
                + v["healing_provided"] * 1.5
                + v["critical_hits"] * 10.0
                - v["fumbles"] * 5.0
                + v["turns_taken"] * 2.0
            )
            combatants.append(
                CombatantPerformance(
                    combatant_id=v["combatant_id"],
                    combatant_name=v["combatant_name"] or v["combatant_id"],
                    damage_dealt=v["damage_dealt"],
                    damage_taken=v["damage_taken"],
                    healing_provided=v["healing_provided"],
                    critical_hits=v["critical_hits"],
                    fumbles=v["fumbles"],
                    turns_taken=v["turns_taken"],
                    mvp_score=round(score, 1),
                )
            )
        combatants.sort(key=lambda c: c.mvp_score, reverse=True)

        awards: list[MvpAward] = []
        if combatants:
            # Most Lethal
            top_dmg = max(combatants, key=lambda c: c.damage_dealt)
            if top_dmg.damage_dealt > 0:
                awards.append(
                    MvpAward(
                        title="Most Lethal",
                        recipient_id=top_dmg.combatant_id,
                        recipient_name=top_dmg.combatant_name,
                        metric_name="damage_dealt",
                        score=top_dmg.damage_dealt,
                        description=f"Dealt {top_dmg.damage_dealt} total combat damage",
                    )
                )
            # Guardian Angel
            top_heal = max(combatants, key=lambda c: c.healing_provided)
            if top_heal.healing_provided > 0:
                awards.append(
                    MvpAward(
                        title="Guardian Angel",
                        recipient_id=top_heal.combatant_id,
                        recipient_name=top_heal.combatant_name,
                        metric_name="healing_provided",
                        score=top_heal.healing_provided,
                        description=f"Restored {top_heal.healing_provided} party hit points",
                    )
                )
            # Nat 20 Master
            top_crit = max(combatants, key=lambda c: c.critical_hits)
            if top_crit.critical_hits > 0:
                awards.append(
                    MvpAward(
                        title="Nat 20 Master",
                        recipient_id=top_crit.combatant_id,
                        recipient_name=top_crit.combatant_name,
                        metric_name="critical_hits",
                        score=top_crit.critical_hits,
                        description=f"Landed {top_crit.critical_hits} critical strikes",
                    )
                )

        overall_mvp: MvpAward | None = None
        if combatants and combatants[0].mvp_score > 0:
            top = combatants[0]
            overall_mvp = MvpAward(
                title="Encounter MVP",
                recipient_id=top.combatant_id,
                recipient_name=top.combatant_name,
                metric_name="mvp_score",
                score=top.mvp_score,
                description=f"Highest combat efficacy ({top.mvp_score} pts)",
            )

        return CampaignMvpResponse(
            campaign_id=campaign_id,
            session_id=session_id,
            encounter_id=encounter_id,
            overall_mvp=overall_mvp,
            awards=awards,
            combatants=combatants,
        )

    async def get_timeline(
        self,
        campaign_id: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> CampaignTimelineResponse:
        """Query chronological event milestones linking session recaps and boss encounters."""
        filtered = [
            m
            for m in self.milestones
            if self._matches_campaign(m["campaign_id"], m["session_id"], campaign_id)
            and (not session_id or m["session_id"] == session_id)
        ]
        # Sort chronologically by timestamp
        filtered.sort(key=lambda m: m["timestamp"])
        selected = filtered[:limit]
        milestones = [
            TimelineMilestone(
                id=m["id"],
                campaign_id=m["campaign_id"],
                session_id=m["session_id"],
                type=m["milestone_type"],
                title=m["title"],
                description=m["description"],
                timestamp=m["timestamp"],
                metadata=m.get("metadata", {}),
            )
            for m in selected
        ]
        return CampaignTimelineResponse(
            campaign_id=campaign_id,
            session_id=session_id,
            total_milestones=len(filtered),
            milestones=milestones,
        )
