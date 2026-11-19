"""Shared fixtures for Campaign Analytics UI blackbox test suite.

The service runs through its real lifespan on a PostgreSQL container and a Redis double
(tests/helpers/campaign_analytics_service.py). Tests publish events and read public routes.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.campaign_analytics_service import AnalyticsService


@pytest.fixture
def spicedb_client(analytics_service: AnalyticsService) -> MockSpiceDBClient:
    return analytics_service.spicedb


@pytest.fixture
def event_bus(analytics_service: AnalyticsService) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=analytics_service.redis)


@pytest.fixture
def client(analytics_service: AnalyticsService) -> Iterator[TestClient]:
    """A member's client over a running service. The lifespan starts the consumers."""
    with analytics_service.start() as running:
        yield running
