"""Blackbox tests: Campaign Analytics fails closed at start-up (TASK-0688, ADR-0015 (f)).

The service starts only when its PostgreSQL store and its Redis transport are reachable. A closed
port is a real refused connection, so no client is replaced. Each case starts the real lifespan
and expects the start-up to raise. No request is served.
"""

from __future__ import annotations

from typing import Any

import pytest
from campaign_analytics.storage import CampaignStoreStartupError
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider, EventBusUnavailableError
from runefoble_platform.event_sourcing import get_event_store, set_event_store

from tests.helpers.module_state import restored_seam
from tests.helpers.ports import free_port


def _closed_port() -> int:
    """Return a local TCP port with no listener. The socket closes before the test uses it."""
    return free_port()


def test_start_up_fails_with_clear_error_when_postgresql_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A closed PostgreSQL port stops start-up with a named store error."""
    import campaign_analytics.main as analytics_main
    from fastapi.testclient import TestClient

    dsn = f"postgresql+asyncpg://u:p@127.0.0.1:{_closed_port()}/analytics"
    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", dsn)
    monkeypatch.setattr(analytics_main, "platform_settings", PlatformSettings())
    with (
        restored_seam(get_event_store, set_event_store, None, replace=True),
        pytest.raises(CampaignStoreStartupError, match="PostgreSQL store is unreachable"),
        TestClient(analytics_main.app),
    ):
        pass


def test_start_up_fails_when_database_url_is_not_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SQLite is not a supported store. The service refuses to start on it."""
    import campaign_analytics.main as analytics_main
    from campaign_analytics.storage import StorageConfigurationError
    from fastapi.testclient import TestClient

    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(analytics_main, "platform_settings", PlatformSettings())
    with (
        restored_seam(get_event_store, set_event_store, None, replace=True),
        pytest.raises(StorageConfigurationError),
        TestClient(analytics_main.app),
    ):
        pass


def test_start_up_fails_when_redis_is_unreachable(
    postgres_service: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With PostgreSQL reachable and Redis on a closed port, start-up fails before serving."""
    import campaign_analytics.main as analytics_main
    from fastapi.testclient import TestClient

    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", str(postgres_service["async_dsn"]))
    monkeypatch.setenv("RUNEFOBLE_REDIS_URL", f"redis://127.0.0.1:{_closed_port()}/0")
    settings = PlatformSettings()
    monkeypatch.setattr(analytics_main, "platform_settings", settings)
    monkeypatch.setattr(analytics_main, "event_bus_provider", EventBusProvider(settings))
    with (
        restored_seam(get_event_store, set_event_store, None, replace=True),
        pytest.raises(EventBusUnavailableError, match="unreachable at start-up"),
        TestClient(analytics_main.app),
    ):
        pass
