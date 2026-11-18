"""Projection transaction: every read-model write for one stream message.

A message's writes and its stream position commit together. A failed write raises and rolls
back the whole message, so a restart replays it and never skips it. Metric row ids derive from
the stream message id, so a replayed write lands on the same row. Milestone row ids are the ids
of their saved chronicle events, so a replayed milestone lands on the same row.

Governed by ADR-0006 (Redis Streams) and ADR-0011 (event sourcing).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection

from campaign_analytics.schema import (
    COMBAT_METRIC_FIELDS,
    combat_perf_table,
    projection_state_table,
    session_campaign_table,
    spatial_table,
    timeline_table,
)

STREAM_POSITION_SCOPE = "stream_position"
TOKEN_POSITION_SCOPE = "token_position"
TOKEN_NAME_SCOPE = "token_name"
ACTIVE_COMBATANT_SCOPE = "active_combatant"
ACTIVE_ENCOUNTER_SCOPE = "active_encounter"
ACTIVE_ROUND_SCOPE = "active_round"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ProjectionTx:
    """Writes for one stream message, bound to one database transaction."""

    def __init__(self, conn: AsyncConnection, stream: str, message_id: str) -> None:
        self._conn = conn
        self.stream = stream
        self.message_id = message_id
        self._sequence = 0

    def _row_id(self, *content: Any) -> str:
        """Derive a row id from the message identity and the row content.

        A replay of the same message writes the same content, so it yields the same id.
        Content in the key stops unrelated rows from colliding on the same id.
        """
        self._sequence += 1
        key = "|".join([self.stream, self.message_id, str(self._sequence), *map(str, content)])
        return str(uuid5(NAMESPACE_URL, f"runefoble:{key}"))

    async def resolve_campaign(self, id_or_session: str) -> str:
        """Return the campaign that owns a session id, or the id itself when none is mapped."""
        q = str(id_or_session)
        stmt = select(session_campaign_table.c.campaign_id).where(
            session_campaign_table.c.session_id == q
        )
        found = (await self._conn.execute(stmt)).scalar_one_or_none()
        return str(found) if found is not None else q

    async def map_session(self, session_id: str, campaign_id: str) -> None:
        if not (session_id and campaign_id):
            return
        stmt = pg_insert(session_campaign_table).values(
            session_id=str(session_id), campaign_id=str(campaign_id)
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[session_campaign_table.c.session_id],
            set_={"campaign_id": stmt.excluded.campaign_id},
        )
        await self._conn.execute(stmt)

    async def add_spatial(
        self,
        campaign_id: str,
        session_id: str,
        token_id: str,
        token_name: str,
        x: int,
        y: int,
        event_type: str,
        damage: int = 0,
    ) -> None:
        stmt = pg_insert(spatial_table).values(
            id=self._row_id(campaign_id, session_id, token_id, x, y, event_type, damage),
            campaign_id=str(campaign_id),
            session_id=str(session_id),
            token_id=str(token_id),
            token_name=token_name,
            x=int(x),
            y=int(y),
            event_type=event_type,
            damage=int(damage),
            recorded_at=_now(),
        )
        await self._conn.execute(stmt.on_conflict_do_nothing(index_elements=["id"]))

    async def add_combatant_stat(
        self,
        campaign_id: str,
        session_id: str,
        encounter_id: str,
        combatant_id: str,
        combatant_name: str,
        **deltas: int,
    ) -> None:
        """Add metric deltas to a combatant's cumulative record for the session."""
        # Combatant rows are upserted on their unique key. Their id is set once, on insert.
        values = dict.fromkeys(COMBAT_METRIC_FIELDS, 0)
        values.update({k: int(v) for k, v in deltas.items() if k in values})
        stmt = pg_insert(combat_perf_table).values(
            id=str(uuid4()),
            campaign_id=str(campaign_id),
            session_id=str(session_id),
            encounter_id=encounter_id or "default",
            combatant_id=str(combatant_id),
            combatant_name=combatant_name,
            updated_at=_now(),
            **values,
        )
        table = combat_perf_table.c
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            constraint="uq_combatant_per_session",
            set_={
                **{f: table[f] + excluded[f] for f in COMBAT_METRIC_FIELDS},
                "combatant_name": func.coalesce(
                    func.nullif(excluded.combatant_name, ""), table.combatant_name
                ),
                "updated_at": excluded.updated_at,
            },
        )
        await self._conn.execute(stmt)

    async def add_milestone(
        self,
        milestone_id: str,
        campaign_id: str,
        session_id: str,
        milestone_type: str,
        title: str,
        description: str,
        timestamp: str,
        metadata: dict[str, Any],
    ) -> None:
        """Project one saved chronicle milestone. Its id is the saved milestone's event id."""
        stmt = pg_insert(timeline_table).values(
            id=milestone_id,
            campaign_id=str(campaign_id),
            session_id=str(session_id),
            milestone_type=milestone_type,
            title=title,
            description=description,
            timestamp=timestamp,
            metadata_json=json.dumps(metadata),
        )
        await self._conn.execute(stmt.on_conflict_do_nothing(index_elements=["id"]))

    async def get_state(self, scope: str, key: str, default: Any = None) -> Any:
        """Read a projection state value that earlier messages stored."""
        stmt = select(projection_state_table.c.value).where(
            projection_state_table.c.scope == scope, projection_state_table.c.key == str(key)
        )
        raw = (await self._conn.execute(stmt)).scalar_one_or_none()
        return default if raw is None else json.loads(raw)

    async def set_state(self, scope: str, key: str, value: Any) -> None:
        await _upsert_state(self._conn, scope, str(key), value)

    async def commit_position(self) -> None:
        """Record this message as projected. Called once, inside the same transaction."""
        await _upsert_state(self._conn, STREAM_POSITION_SCOPE, self.stream, self.message_id)


async def _upsert_state(conn: AsyncConnection, scope: str, key: str, value: Any) -> None:
    stmt = pg_insert(projection_state_table).values(scope=scope, key=key, value=json.dumps(value))
    stmt = stmt.on_conflict_do_update(
        index_elements=[projection_state_table.c.scope, projection_state_table.c.key],
        set_={"value": stmt.excluded.value},
    )
    await conn.execute(stmt)
