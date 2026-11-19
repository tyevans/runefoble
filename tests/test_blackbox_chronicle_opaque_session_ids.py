"""Blackbox test: the chronicle recap keeps one aggregate id per session (TASK-0816).

The Watcher treats session ids as opaque strings. A recap for the same session must
land on the same aggregate stream on every call. A random id per call would split the
session history across streams.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.helpers.spicedb_factory import bind_character_owner, make_table_runner
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_recap_for_opaque_session_id_reuses_one_aggregate_id():
    """Two recaps for one opaque session id carry the same aggregate id."""
    session_id = f"sess-chronicle-{uuid4().hex[:8]}"
    asyncio.run(make_table_runner("test-user", session_id, str(uuid4())))
    asyncio.run(bind_character_owner("test-user", "p-1"))
    client = TestClient(
        watcher_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
    body = {
        "session_id": session_id,
        "character_id": str(uuid4()),
        "character_name": "Elidor",
        "actions": [],
    }

    first = client.post("/api/v1/watcher/chronicle/recap", json=body)
    second = client.post("/api/v1/watcher/chronicle/recap", json=body)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]
