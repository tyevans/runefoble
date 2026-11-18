"""Blackbox frontdoor tests for durable Audience Studio poll state and Redis publish recovery.

Governed by:
- TASK-0575: Audience Studio poll and proposal state durable, with Redis publish recovery
- ADR-0006: Redis Streams event streaming
- ADR-0011: Event sourcing (durable store in deployment)
- Hard Invariant 7: Blackbox TDD with frontdoor setup

Only public HTTP routes, process restarts, and the published Redis Stream are used.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator

import httpx
import pytest
import redis

from tests.helpers.audience_server import AudienceStudioProcess, bearer_for
from tests.helpers.ports import free_port
from tests.helpers.redis_container import redis_container
from tests.helpers.spicedb import LiveSpiceDB

STREAM = "runefoble.events.audience"
POLLS = "/api/v1/audience/polls"


def _create_poll(client: httpx.Client, **overrides: object) -> dict:
    body: dict[str, object] = {
        "campaign_id": "camp-durable",
        "title": "Durable Poll",
        "prompt": "Does state survive?",
        "options": ["Yes", "No"],
        "duration_seconds": 600,
        "quorum": 1,
    }
    body.update(overrides)
    res = client.post(POLLS, headers=bearer_for("dm-durable"), json=body)
    assert res.status_code == 201, res.text
    return res.json()


def _stream_events(redis_url: str, event_type: str) -> list[dict[str, str]]:
    client = redis.Redis.from_url(redis_url)
    entries = client.xrange(STREAM)
    return [
        {k.decode(): v.decode() for k, v in fields.items()}
        for _, fields in entries
        if fields.get(b"event_type", b"").decode().endswith(event_type)
    ]


@pytest.fixture
def database_url(postgres_service) -> Generator[str]:
    yield str(postgres_service["dsn"])


@pytest.fixture(scope="module")
def roles(live_spicedb_with_schema: LiveSpiceDB) -> LiveSpiceDB:
    """Grants the campaign roles these scenarios use, written into the live SpiceDB container."""
    spicedb = live_spicedb_with_schema
    spicedb.grant("camp-durable", "dungeon_master", "dm-durable")
    spicedb.grant("camp-durable", "spectator", "viewer-restart")
    spicedb.grant("camp-durable", "spectator", "viewer-window")
    spicedb.grant("camp-recover", "dungeon_master", "dm-durable")
    spicedb.grant("camp-recover", "spectator", "viewer-recover")
    return spicedb


def test_poll_and_votes_survive_a_restart(database_url: str, roles: LiveSpiceDB):
    """A poll and its votes are read back after the service restarts."""
    process = AudienceStudioProcess({"RUNEFOBLE_DATABASE_URL": database_url, **roles.env})
    base_url = process.start()
    try:
        with httpx.Client(base_url=base_url) as client:
            poll = _create_poll(client, title="Survives Restart")
            vote = client.post(
                f"{POLLS}/{poll['id']}/votes",
                headers=bearer_for("viewer-restart"),
                json={"option_id": "opt_1"},
            )
            assert vote.status_code == 200
    finally:
        process.stop()

    restarted = AudienceStudioProcess({"RUNEFOBLE_DATABASE_URL": database_url, **roles.env})
    base_url = restarted.start()
    try:
        with httpx.Client(base_url=base_url) as client:
            read = client.get(f"{POLLS}/{poll['id']}", headers=bearer_for("dm-durable"))
            assert read.status_code == 200
            body = read.json()
            assert body["status"] == "active"
            assert body["totalVotes"] == 1
            assert body["options"][0]["votes"] == 1
    finally:
        restarted.stop()


def test_short_window_poll_closes_after_restart_and_publishes_completion(
    database_url: str, roles: LiveSpiceDB
):
    """A poll whose window ends while the service is down closes on restart and emits completion."""
    with redis_container(free_port()) as redis_url:
        process = AudienceStudioProcess(
            {"RUNEFOBLE_DATABASE_URL": database_url, "REDIS_URL": redis_url, **roles.env}
        )
        base_url = process.start()
        try:
            with httpx.Client(base_url=base_url) as client:
                poll = _create_poll(client, duration_seconds=2, quorum=1, title="Closes Later")
                vote = client.post(
                    f"{POLLS}/{poll['id']}/votes",
                    headers=bearer_for("viewer-window"),
                    json={"option_id": "opt_2"},
                )
                assert vote.status_code == 200
        finally:
            process.stop()

        time.sleep(2.5)

        restarted = AudienceStudioProcess(
            {"RUNEFOBLE_DATABASE_URL": database_url, "REDIS_URL": redis_url, **roles.env}
        )
        base_url = restarted.start()
        try:
            deadline = time.time() + 10
            completed: list[dict[str, str]] = []
            while time.time() < deadline and not completed:
                completed = [
                    e
                    for e in _stream_events(redis_url, "poll_completed")
                    if poll["id"] in e["payload"]
                ]
                time.sleep(0.2)
            assert len(completed) == 1
            event = json.loads(completed[0]["payload"])
            assert event["type"] == "runefoble.events.audience.poll_completed"
            assert event["data"]["winning_option_id"] == "opt_2"
            assert event["data"]["quorum_met"] is True

            with httpx.Client(base_url=base_url) as client:
                read = client.get(f"{POLLS}/{poll['id']}", headers=bearer_for("dm-durable")).json()
            assert read["status"] == "completed"
        finally:
            restarted.stop()


def test_publishing_recovers_when_redis_starts_after_the_service(
    database_url: str, roles: LiveSpiceDB
):
    """A write made while Redis is down succeeds, and the outbox relay publishes it once Redis is up."""
    port = free_port()
    process = AudienceStudioProcess(
        {
            "RUNEFOBLE_DATABASE_URL": database_url,
            "REDIS_URL": f"redis://127.0.0.1:{port}/0",
            **roles.env,
        }
    )
    base_url = process.start()
    try:
        with httpx.Client(base_url=base_url) as client:
            assert client.get("/readyz").status_code == 503

            accepted = client.post(
                POLLS,
                headers=bearer_for("dm-durable"),
                json={
                    "campaign_id": "camp-recover",
                    "title": "While Down",
                    "prompt": "P",
                    "options": ["A"],
                },
            )
            assert accepted.status_code == 201, accepted.text
            pending_id = accepted.json()["id"]

            with redis_container(port) as redis_url:
                process.wait_for_status("/readyz", 200, timeout=20.0)

                deadline = time.time() + 15
                created: list[dict[str, str]] = []
                while time.time() < deadline and not created:
                    created = [
                        e
                        for e in _stream_events(redis_url, "poll_started")
                        if pending_id in e["payload"]
                    ]
                    time.sleep(0.2)
                assert len(created) == 1

                poll = _create_poll(client, campaign_id="camp-recover", title="After Recovery")
                vote = client.post(
                    f"{POLLS}/{poll['id']}/votes",
                    headers=bearer_for("viewer-recover"),
                    json={"option_id": "opt_1"},
                )
                assert vote.status_code == 200

                cast = [
                    e for e in _stream_events(redis_url, "vote_cast") if poll["id"] in e["payload"]
                ]
                assert len(cast) == 1
    finally:
        process.stop()
