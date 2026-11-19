"""Blackbox tests for the pending action expiry timer during a store outage (TASK-0915).

The expiry timer retries a store outage a fixed number of times. After the limit it stops,
and the action stays open in the store. A short outage inside the limit does not stop the
timer: the action expires when the store answers again.

The app serves the production container with one change: its copilot engine has a short
retry interval, so the test does not wait seconds. Each test reads the result only through
the public pending-action route.
"""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from runefoble_auth.factory import get_spicedb_client
from the_watcher.copilot import CopilotEngine

from tests.helpers.event_store_seam import store_outage
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import bind_session_to_campaign
from tests.helpers.the_watcher_app import app_with_container, build_test_container
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

RETRY_SECONDS = 0.05
MAX_RETRIES = 3
PAUSE_WINDOW_MS = 100


@pytest.fixture(autouse=True)
def redis_double(use_redis_client) -> None:
    use_redis_client(MockAsyncRedis())


@pytest.fixture
def app() -> Iterator[FastAPI]:
    container = build_test_container()
    engine = CopilotEngine(
        pending_repo=container.repositories.pending_actions,
        retry_seconds=RETRY_SECONDS,
        max_retries=MAX_RETRIES,
    )
    served = app_with_container(dataclasses.replace(container, copilot=engine))
    yield served
    engine.shutdown()


def _headers(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(user)}"}


async def _dm_table() -> tuple[str, str, str]:
    dm, camp_id, sess_id = f"dm-{uuid4().hex[:6]}", str(uuid4()), str(uuid4())
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm,
    )
    await bind_session_to_campaign(sess_id, camp_id)
    return dm, camp_id, sess_id


async def _propose(ac: AsyncClient, dm: str, camp_id: str, sess_id: str) -> str:
    res = await ac.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": sess_id,
            "campaign_id": camp_id,
            "actor_name": "Goblin",
            "action_type": "attack",
            "description": "Attacks target",
            "pause_window_ms": PAUSE_WINDOW_MS,
        },
        headers=_headers(dm),
    )
    assert res.status_code == 200, res.text
    return res.json()["action_id"]


async def _status(ac: AsyncClient, dm: str, camp_id: str, sess_id: str, action_id: str) -> str:
    res = await ac.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers=_headers(dm),
    )
    assert res.status_code == 200, res.text
    return next(a["status"] for a in res.json() if a["action_id"] == action_id)


@pytest.mark.asyncio
async def test_expiry_timer_stops_after_the_retry_limit(app: FastAPI):
    """An outage longer than the retry limit stops the timer. The action stays pending."""
    dm, camp_id, sess_id = await _dm_table()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        action_id = await _propose(ac, dm, camp_id, sess_id)
        with store_outage():
            await asyncio.sleep(PAUSE_WINDOW_MS / 1000 + RETRY_SECONDS * (MAX_RETRIES + 4))
        await asyncio.sleep(RETRY_SECONDS * 6)

        assert await _status(ac, dm, camp_id, sess_id, action_id) == "pending"


@pytest.mark.asyncio
async def test_expiry_timer_recovers_from_an_outage_inside_the_limit(app: FastAPI):
    """An outage shorter than the retry limit is retried. The action then expires."""
    dm, camp_id, sess_id = await _dm_table()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        action_id = await _propose(ac, dm, camp_id, sess_id)
        with store_outage():
            await asyncio.sleep(PAUSE_WINDOW_MS / 1000 + RETRY_SECONDS / 2)

        status = "pending"
        for _ in range(40):
            await asyncio.sleep(RETRY_SECONDS)
            status = await _status(ac, dm, camp_id, sess_id, action_id)
            if status != "pending":
                break

    assert status == "executed"
