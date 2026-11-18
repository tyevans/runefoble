"""SQLAlchemy Core tables for Campaign Analytics read models and projection state.

Every read model is a PostgreSQL table. Projection writes and the stream position commit in
one transaction, so a restart resumes exactly after the last projected message.

Governed by ADR-0011 and ADR-0015 (PostgreSQL is mandatory in deployed environments).
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
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
    Column("campaign_id", String(64), nullable=False),
    Column("session_id", String(64), nullable=False),
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
    UniqueConstraint("campaign_id", "session_id", "combatant_id", name="uq_combatant_per_session"),
    Index("ix_combat_perf_campaign", "campaign_id"),
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

session_campaign_table = Table(
    "campaign_session_map",
    metadata,
    Column("session_id", String(64), primary_key=True),
    Column("campaign_id", String(64), index=True, nullable=False),
)

projection_state_table = Table(
    "analytics_projection_state",
    metadata,
    Column("scope", String(32), primary_key=True),
    Column("key", String(256), primary_key=True),
    Column("value", Text, nullable=False),
)

COMBAT_METRIC_FIELDS = (
    "damage_dealt",
    "damage_taken",
    "healing_provided",
    "critical_hits",
    "fumbles",
    "turns_taken",
)
