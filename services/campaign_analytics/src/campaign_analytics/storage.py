"""PostgreSQL storage for Campaign Analytics read models.

The engine is created at start-up and must connect and create its tables. A failure raises, so
the service does not start. Queries read the read-model tables directly. No query reads
process memory.

Governed by ADR-0011, ADR-0015 (no silent in-memory fallback), and Hard Invariant 6.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import normalize_async_postgres_url
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from campaign_analytics.models import (
    CampaignHeatmapResponse,
    CampaignMvpResponse,
    CampaignTimelineResponse,
)
from campaign_analytics.projection import STREAM_POSITION_SCOPE, ProjectionTx
from campaign_analytics.queries import (
    calculate_mvp_rankings,
    query_campaign_timeline,
    query_spatial_heatmap,
)
from campaign_analytics.schema import (
    combat_perf_table,
    metadata,
    projection_state_table,
    session_campaign_table,
    spatial_table,
    timeline_table,
)


class StorageConfigurationError(RuntimeError):
    """Raised when the configured database cannot hold campaign analytics read models."""


class StorageUnavailableError(RuntimeError):
    """Raised when a query runs before the storage engine is ready."""


def campaign_match(table: Any, campaign_id: str) -> Any:
    """Match rows that belong to a campaign id, or to a session that belongs to it.

    A query id matches when it names the row's campaign or session. It also matches when the
    row's session maps to it, or when the query names a session whose campaign is the row's.
    """
    q = str(campaign_id)
    sessions_of_q = select(session_campaign_table.c.session_id).where(
        session_campaign_table.c.campaign_id == q
    )
    campaign_of_q = select(session_campaign_table.c.campaign_id).where(
        session_campaign_table.c.session_id == q
    )
    return or_(
        table.c.campaign_id == q,
        table.c.session_id == q,
        table.c.session_id.in_(sessions_of_q),
        table.c.campaign_id.in_(campaign_of_q),
    )


def _session_filter(table: Any, session_id: str | None) -> list[Any]:
    return [table.c.session_id == str(session_id)] if session_id else []


class CampaignAnalyticsStorage:
    """Durable projection storage and read queries for campaign analytics."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    @classmethod
    async def create(cls, settings: PlatformSettings) -> CampaignAnalyticsStorage:
        """Connect to PostgreSQL and create the read-model tables. Errors propagate."""
        url = str(settings.database_url)
        if "postgresql" not in url:
            raise StorageConfigurationError(
                "Campaign analytics requires PostgreSQL. SQLite and in-memory storage are not supported."
            )
        engine = create_async_engine(
            normalize_async_postgres_url(url),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        try:
            async with engine.begin() as conn:
                await conn.run_sync(metadata.create_all)
        except BaseException:
            await engine.dispose()
            raise
        return cls(engine)

    async def dispose(self) -> None:
        await self.engine.dispose()

    @contextlib.asynccontextmanager
    async def projection(self, stream: str, message_id: str) -> AsyncIterator[ProjectionTx]:
        """Open one transaction for a stream message. The stream position commits with it."""
        async with self.engine.begin() as conn:
            tx = ProjectionTx(conn, stream, message_id)
            yield tx
            await tx.commit_position()

    async def stream_position(self, stream: str) -> str | None:
        """Return the id of the last message projected from a stream, or None."""
        stmt = select(projection_state_table.c.value).where(
            projection_state_table.c.scope == STREAM_POSITION_SCOPE,
            projection_state_table.c.key == stream,
        )
        async with self.engine.connect() as conn:
            raw = (await conn.execute(stmt)).scalar_one_or_none()
        return None if raw is None else str(json.loads(raw))

    async def counts(self) -> dict[str, int]:
        """Count rows in each read model."""
        async with self.engine.connect() as conn:
            return {
                "spatial_records_count": await _count(conn, spatial_table),
                "combatants_count": await _count(conn, combat_perf_table),
                "milestones_count": await _count(conn, timeline_table),
            }

    async def get_heatmap(
        self,
        campaign_id: str,
        session_id: str | None = None,
        cell_size: int = 5,
        metric: str = "all",
    ) -> CampaignHeatmapResponse:
        stmt = (
            select(spatial_table)
            .where(campaign_match(spatial_table, campaign_id))
            .where(*_session_filter(spatial_table, session_id))
        )
        rows = await self._rows(stmt)
        return query_spatial_heatmap(rows, campaign_id, session_id, cell_size, metric)

    async def get_mvp(
        self,
        campaign_id: str,
        session_id: str | None = None,
        encounter_id: str | None = None,
    ) -> CampaignMvpResponse:
        stmt = select(combat_perf_table).where(campaign_match(combat_perf_table, campaign_id))
        stmt = stmt.where(*_session_filter(combat_perf_table, session_id))
        if encounter_id:
            stmt = stmt.where(combat_perf_table.c.encounter_id == encounter_id)
        rows = await self._rows(stmt)
        return calculate_mvp_rankings(rows, campaign_id, session_id, encounter_id)

    async def get_timeline(
        self, campaign_id: str, session_id: str | None = None, limit: int = 50
    ) -> CampaignTimelineResponse:
        stmt = select(timeline_table).where(campaign_match(timeline_table, campaign_id))
        stmt = stmt.where(*_session_filter(timeline_table, session_id))
        rows = await self._rows(stmt.order_by(timeline_table.c.timestamp))
        return query_campaign_timeline(rows, campaign_id, session_id, limit)

    async def _rows(self, stmt: Any) -> list[dict[str, Any]]:
        async with self.engine.connect() as conn:
            return [dict(row) for row in (await conn.execute(stmt)).mappings().all()]


async def _count(conn: Any, table: Any) -> int:
    return int((await conn.execute(select(func.count()).select_from(table))).scalar_one())
