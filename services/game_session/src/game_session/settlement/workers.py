"""Aggregator facade re-exporting settlement workers for backward compatibility."""

from __future__ import annotations

from game_session.settlement.worker_aggregate import NPCWorkerAggregate

__all__ = ["NPCWorkerAggregate"]
