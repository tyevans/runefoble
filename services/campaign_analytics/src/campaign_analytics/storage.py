"""Persistent analytical storage engine for Campaign Analytics read-models.

Governed by ADR-0005, ADR-0011, and Hard Invariant 6 (< 160 lines).
"""

from __future__ import annotations

import logging
from typing import Any

from runefoble_platform.config import PlatformSettings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from campaign_analytics.models import (
    CampaignHeatmapResponse,
    CampaignMvpResponse,
    CampaignTimelineResponse,
)
from campaign_analytics.queries import (
    calculate_mvp_rankings,
    create_milestone_record,
    create_spatial_record,
    query_campaign_timeline,
    query_spatial_heatmap,
)
from campaign_analytics.schema import (
    apply_combatant_metrics,
    metadata,
    spatial_table,
    timeline_table,
)

logger = logging.getLogger("runefoble.campaign_analytics.storage")


class CampaignAnalyticsStorage:
    """Analytical read-model projection storage supporting PostgreSQL and in-memory fallback."""

    def __init__(self, engine: AsyncEngine | None = None, database_url: str | None = None) -> None:
        self.engine, self._db_url = engine, database_url
        self.session_to_campaign: dict[str, str] = {}
        self.spatial_records: list[dict[str, Any]] = []
        self.combatants: dict[str, dict[str, Any]] = {}
        self.milestones: list[dict[str, Any]] = []

    @classmethod
    async def create(cls, settings: PlatformSettings | None = None) -> CampaignAnalyticsStorage:
        db_url = str((settings or PlatformSettings()).database_url)
        engine = None
        if "postgresql" in db_url:
            try:
                engine = create_async_engine(db_url, pool_size=5, max_overflow=10)
                async with engine.begin() as conn:
                    await conn.run_sync(metadata.create_all)
                logger.info("Connected to PostgreSQL analytical database.")
            except Exception as e:
                logger.warning("PostgreSQL unreachable (%s). Using in-memory fallback.", e)
        return cls(engine=engine, database_url=db_url)

    def map_session(self, session_id: str, campaign_id: str) -> None:
        if session_id and campaign_id:
            self.session_to_campaign[str(session_id)] = str(campaign_id)

    def resolve_campaign_id(self, id_or_session: str) -> str:
        return self.session_to_campaign.get(str(id_or_session), str(id_or_session))

    def _matches_campaign(self, rec_c: str, rec_s: str, query_id: str) -> bool:
        q, s = str(query_id), self.session_to_campaign
        return rec_c == q or rec_s == q or s.get(rec_s) == q or s.get(q) == rec_c

    async def _insert_row(self, table: Any, values: dict[str, Any]) -> None:
        if self.engine:
            try:
                async with self.engine.begin() as conn:
                    await conn.execute(table.insert().values(values))
            except Exception as e:
                logger.debug("Failed asyncpg write to %s: %s", table.name, e)

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
        rec = create_spatial_record(
            campaign_id, session_id, token_id, token_name, x, y, event_type, damage, recorded_at
        )
        self.spatial_records.append(rec)
        await self._insert_row(spatial_table, rec)

    async def record_combatant_stat(
        self,
        campaign_id: str,
        session_id: str,
        encounter_id: str,
        combatant_id: str,
        combatant_name: str,
        *args: int,
        **kwargs: int,
    ) -> None:
        apply_combatant_metrics(
            self.combatants,
            campaign_id,
            session_id,
            encounter_id,
            combatant_id,
            combatant_name,
            *args,
            **kwargs,
        )

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
        rec, vals = create_milestone_record(
            campaign_id, session_id, milestone_type, title, description, timestamp, metadata_dict
        )
        self.milestones.append(rec)
        await self._insert_row(timeline_table, vals)

    async def get_heatmap(
        self,
        campaign_id: str,
        session_id: str | None = None,
        cell_size: int = 5,
        metric: str = "all",
    ) -> CampaignHeatmapResponse:
        m = self._matches_campaign
        return query_spatial_heatmap(
            self.spatial_records, campaign_id, session_id, cell_size, metric, m
        )

    async def get_mvp(
        self,
        campaign_id: str,
        session_id: str | None = None,
        encounter_id: str | None = None,
    ) -> CampaignMvpResponse:
        m = self._matches_campaign
        return calculate_mvp_rankings(self.combatants, campaign_id, session_id, encounter_id, m)

    async def get_timeline(
        self, campaign_id: str, session_id: str | None = None, limit: int = 50
    ) -> CampaignTimelineResponse:
        return query_campaign_timeline(
            self.milestones, campaign_id, session_id, limit, self._matches_campaign
        )

    record_spatial_position = record_spatial
    get_campaign_heatmaps = get_heatmap
    get_campaign_mvp = get_mvp
    get_campaign_timeline = get_timeline
