"""Blackbox test: a malformed settlement id is refused before any write (TASK-0816).

Drives only the public settlement upgrade route. A path id that is not a UUID returns 400
with the field name. The route never loads a made-up aggregate, and it publishes nothing.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers.mock_redis import MockAsyncRedis

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_malformed_settlement_id_is_refused_before_any_write(
    client: TestClient, mock_bus: MockAsyncRedis
):
    """A bad settlement id returns 400 and names the field. No event is published."""
    resp = client.post(
        "/api/v1/settlements/not-a-uuid/upgrade",
        json={"facility_id": "workshop"},
    )

    assert resp.status_code == 400, resp.text
    assert "settlement_id" in resp.text
    assert not mock_bus.streams
