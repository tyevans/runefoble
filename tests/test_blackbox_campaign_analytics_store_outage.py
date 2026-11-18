"""Blackbox test: Campaign Analytics answers 503 when its PostgreSQL store goes away.

Governed by ADR-0015 (fail closed) and Hard Invariant 7. The store is a real container. This
module owns its container, so stopping it does not affect other test modules.
"""

from __future__ import annotations

import shutil
import subprocess
from uuid import uuid4

import pytest

from tests.helpers.campaign_analytics_service import AnalyticsService


def test_query_route_returns_503_after_store_stops(
    analytics_service: AnalyticsService, postgres_service: dict[str, str | int]
) -> None:
    """A query that needs the store fails with 503 once the store is unreachable."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        pytest.skip("Docker not available to stop the PostgreSQL store")

    cid = str(uuid4())
    analytics_service.grant_view(cid)
    url = f"/api/v1/analytics/campaigns/{cid}/timeline"

    with analytics_service.start() as client:
        assert client.get(url).status_code == 200

        subprocess.run(
            [docker_bin, "stop", str(postgres_service["container_name"])],
            check=True,
            capture_output=True,
        )

        resp = client.get(url)
        assert resp.status_code == 503, resp.text
        assert "unavailable" in resp.json()["detail"]
