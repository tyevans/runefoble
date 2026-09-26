"""SQLAlchemy Core relational tables for Campaign Analytics analytical read-models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

spatial_table = Table(
    "campaign_spatial_telemetry",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("campaign_id", String(64), index=True, nullable=False),
    Column("session_id", String(64), index=True, nullable=False),
    Column("token_id", String(64), nullable=False),
    Column("token_name", String(128), default=""),
    Column("x", Integer, nullable=False),
    Column("y", Integer, nullable=False),
    Column("event_type", String(32), default="movement"),
    Column("damage", Integer, default=0),
    Column("recorded_at", String(64), nullable=False),
)

combat_perf_table = Table(
    "combat_performance_records",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("campaign_id", String(64), index=True, nullable=False),
    Column("session_id", String(64), index=True, nullable=False),
    Column("encounter_id", String(64), default="default"),
    Column("combatant_id", String(64), nullable=False),
    Column("combatant_name", String(128), default=""),
    Column("damage_dealt", Integer, default=0),
    Column("damage_taken", Integer, default=0),
    Column("healing_provided", Integer, default=0),
    Column("critical_hits", Integer, default=0),
    Column("fumbles", Integer, default=0),
    Column("turns_taken", Integer, default=0),
    Column("updated_at", String(64), nullable=False),
)

timeline_table = Table(
    "campaign_timeline_milestones",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("campaign_id", String(64), index=True, nullable=False),
    Column("session_id", String(64), index=True, nullable=False),
    Column("milestone_type", String(64), nullable=False),
    Column("title", String(256), nullable=False),
    Column("description", Text, default=""),
    Column("timestamp", String(64), nullable=False),
    Column("metadata_json", Text, default="{}"),
)

COMBAT_METRIC_FIELDS = (
    "damage_dealt",
    "damage_taken",
    "healing_provided",
    "critical_hits",
    "fumbles",
    "turns_taken",
)


def apply_combatant_metrics(
    combatants: dict[str, dict[str, Any]],
    campaign_id: str,
    session_id: str,
    encounter_id: str,
    combatant_id: str,
    combatant_name: str,
    *args: int,
    **kwargs: int,
) -> None:
    """Initialize or accumulate combatant performance metric deltas."""
    cid, key = str(combatant_id), f"{campaign_id}:{session_id}:{combatant_id}"
    entry = combatants.setdefault(
        key,
        {
            "id": str(uuid4()),
            "campaign_id": str(campaign_id),
            "session_id": str(session_id),
            "encounter_id": encounter_id or "default",
            "combatant_id": cid,
            "combatant_name": combatant_name,
            **dict.fromkeys(COMBAT_METRIC_FIELDS, 0),
        },
    )
    if combatant_name:
        entry["combatant_name"] = combatant_name
    for f, v in zip(COMBAT_METRIC_FIELDS, args, strict=False):
        entry[f] += v
    for f, v in kwargs.items():
        if f in entry:
            entry[f] += v
    entry["updated_at"] = datetime.now(UTC).isoformat()
