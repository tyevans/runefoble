"""Shared fixtures for Campaign Analytics UI blackbox test suite.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from campaign_analytics.dependencies import set_spicedb_client, set_storage, set_worker
from campaign_analytics.main import app
from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def consumer_group(mock_redis: MockAsyncRedis) -> RedisConsumerGroup:
    return RedisConsumerGroup(client=mock_redis)


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=mock_redis)


@pytest.fixture
def storage() -> CampaignAnalyticsStorage:
    return CampaignAnalyticsStorage()


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    return MockSpiceDBClient()


@pytest.fixture
def worker(
    storage: CampaignAnalyticsStorage, consumer_group: RedisConsumerGroup
) -> CampaignAnalyticsWorker:
    return CampaignAnalyticsWorker(
        storage=storage,
        consumer_group=consumer_group,
        group_name="test_ui_analytics_workers",
        consumer_name="test_ui_worker_1",
    )


@pytest.fixture
def client(
    storage: CampaignAnalyticsStorage,
    worker: CampaignAnalyticsWorker,
    spicedb_client: MockSpiceDBClient,
) -> TestClient:
    set_storage(storage)
    set_worker(worker)
    set_spicedb_client(spicedb_client)
    return TestClient(app)
