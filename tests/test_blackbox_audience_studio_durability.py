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

from tests.helpers.audience_server import AudienceStudioProcess, get_free_port
from tests.helpers.redis_container import redis_container

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
    res = client.post(POLLS, json=body)
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
    if not postgres_service:
        pytest.skip("Docker is required for the PostgreSQL event store")
    yield str(postgres_service["dsn"])


def test_poll_and_votes_survive_a_restart(database_url: str):
    """A poll and its votes are read back after the service restarts."""
    process = AudienceStudioProcess({"RUNEFOBLE_DATABASE_URL": database_url})
    base_url = process.start()
    try:
        with httpx.Client(base_url=base_url) as client:
            poll = _create_poll(client, title="Survives Restart")
            vote = client.post(
                f"{POLLS}/{poll['id']}/votes",
                json={"voter_id": "viewer-restart", "option_id": "opt_1"},
            )
            assert vote.status_code == 200
    finally:
        process.stop()

    restarted = AudienceStudioProcess({"RUNEFOBLE_DATABASE_URL": database_url})
    base_url = restarted.start()
    try:
        with httpx.Client(base_url=base_url) as client:
            read = client.get(f"{POLLS}/{poll['id']}")
            assert read.status_code == 200
            body = read.json()
            assert body["status"] == "active"
            assert body["totalVotes"] == 1
            assert body["options"][0]["votes"] == 1
    finally:
        restarted.stop()


def test_short_window_poll_closes_after_restart_and_publishes_completion(database_url: str):
    """A poll whose window ends while the service is down closes on restart and emits completion."""
    with redis_container(get_free_port()) as redis_url:
        process = AudienceStudioProcess(
            {"RUNEFOBLE_DATABASE_URL": database_url, "REDIS_URL": redis_url}
        )
        base_url = process.start()
        try:
            with httpx.Client(base_url=base_url) as client:
                poll = _create_poll(client, duration_seconds=2, quorum=1, title="Closes Later")
                vote = client.post(
                    f"{POLLS}/{poll['id']}/votes",
                    json={"voter_id": "viewer-window", "option_id": "opt_2"},
                )
                assert vote.status_code == 200
        finally:
            process.stop()

        time.sleep(2.5)

        restarted = AudienceStudioProcess(
            {"RUNEFOBLE_DATABASE_URL": database_url, "REDIS_URL": redis_url}
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
                read = client.get(f"{POLLS}/{poll['id']}").json()
            assert read["status"] == "completed"
        finally:
            restarted.stop()


def test_publishing_recovers_when_redis_starts_after_the_service(database_url: str):
    """The service starts before Redis, refuses writes with 503, and publishes once Redis is up."""
    port = get_free_port()
    process = AudienceStudioProcess(
        {"RUNEFOBLE_DATABASE_URL": database_url, "REDIS_URL": f"redis://127.0.0.1:{port}/0"}
    )
    base_url = process.start()
    try:
        with httpx.Client(base_url=base_url) as client:
            assert client.get("/readyz").status_code == 503

            refused = client.post(
                POLLS,
                json={"campaign_id": "camp-recover", "title": "T", "prompt": "P", "options": ["A"]},
            )
            assert refused.status_code == 503

            with redis_container(port) as redis_url:
                process.wait_for_status("/readyz", 200, timeout=20.0)

                poll = _create_poll(client, campaign_id="camp-recover", title="After Recovery")
                vote = client.post(
                    f"{POLLS}/{poll['id']}/votes",
                    json={"voter_id": "viewer-recover", "option_id": "opt_1"},
                )
                assert vote.status_code == 200

                cast = [
                    e for e in _stream_events(redis_url, "vote_cast") if poll["id"] in e["payload"]
                ]
                assert len(cast) == 1
    finally:
        process.stop()
