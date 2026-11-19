"""Blackbox tests: Campaign Analytics fails closed at start-up (TASK-0688, ADR-0015 (f)).

The service starts only when its PostgreSQL store and its Redis transport are reachable. A closed
port is a real refused connection, so no client is replaced. Each case builds the app through the
public factory `create_app` with settings read from the environment, then starts the real lifespan.
No test patches a module attribute of the service.
"""

from __future__ import annotations

from typing import Any

import pytest
from campaign_analytics.main import create_app_from_environment
from campaign_analytics.storage import CampaignStoreStartupError, StorageConfigurationError
from fastapi.testclient import TestClient
from runefoble_platform.event_bus import EventBusUnavailableError
from runefoble_platform.event_sourcing import get_event_store, set_event_store

from tests.helpers.campaign_analytics_service import AnalyticsService
from tests.helpers.module_state import restored_seam
from tests.helpers.ports import free_port


def _closed_port() -> int:
    """Return a local TCP port with no listener. The socket closes before the test uses it."""
    return free_port()


def test_start_up_fails_with_clear_error_when_postgresql_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A closed PostgreSQL port stops start-up with a named store error."""
    dsn = f"postgresql+asyncpg://u:p@127.0.0.1:{_closed_port()}/analytics"
    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", dsn)
    with (
        restored_seam(get_event_store, set_event_store, None, replace=True),
        pytest.raises(CampaignStoreStartupError, match="PostgreSQL store is unreachable"),
        TestClient(create_app_from_environment()),
    ):
        pass


def test_start_up_fails_when_database_url_is_not_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SQLite is not a supported store. The factory refuses to build the service on it."""
    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    with (
        restored_seam(get_event_store, set_event_store, None, replace=True),
        pytest.raises(StorageConfigurationError, match="Campaign analytics requires PostgreSQL"),
        TestClient(create_app_from_environment()),
    ):
        pass


def test_start_up_fails_when_redis_is_unreachable(
    postgres_service: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With PostgreSQL reachable and Redis on a closed port, start-up fails before serving."""
    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", str(postgres_service["async_dsn"]))
    monkeypatch.setenv("RUNEFOBLE_REDIS_URL", f"redis://127.0.0.1:{_closed_port()}/0")
    with (
        restored_seam(get_event_store, set_event_store, None, replace=True),
        pytest.raises(EventBusUnavailableError, match="unreachable at start-up"),
        TestClient(create_app_from_environment()),
    ):
        pass


def test_valid_environment_settings_serve_openapi_document(
    analytics_service: AnalyticsService,
) -> None:
    """With valid environment settings, the factory-built service serves its OpenAPI document."""
    with analytics_service.start(authenticated=False) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"].startswith("Runefoble - Campaign Analytics")
