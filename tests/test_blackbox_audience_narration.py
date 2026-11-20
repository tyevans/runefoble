"""Blackbox frontdoor tests: The Watcher narrates an approved audience modifier (TASK-0838).

The approved modifier is published as the standard `AudienceModifierApproved` event on
`runefoble.events.audience`. The narration is read through the public whisper route, and the
DM dispatch is read from the published `WatcherNarrativeDispatched` event. The inference worker
runs as a live loopback app at the process boundary (no client is patched). Redis is the only
other double. Session-to-campaign links are written through the schema tuples that the Watcher
tests already use. Governed by ADR-0006, ADR-0007, ADR-0011 and ADR-0015.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.the_watcher_app import app_with_container, fresh_store_container
from tests.helpers.ws_identity import bearer

AUDIENCE_STREAM = "runefoble.events.audience"
AUDIENCE_DLQ = f"{AUDIENCE_STREAM}.dlq"
WATCHER_STREAM = "runefoble.events.watcher"
NARRATIVE_DISPATCHED = "runefoble.events.watcher.narrative_dispatched"

DM = "dm-evelyn"
PLAYER = "valeros"
NARRATION = "Fog rolls over the crypt steps and swallows the torchlight."
SENSORY = ["cold damp air", "a distant bell"]

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@dataclass
class WorkerDouble:
    """A loopback inference worker. The test sets its reply and reads the requests it got."""

    url: str = ""
    status: int = 200
    requests: list[dict[str, Any]] = field(default_factory=list)


def _worker_app(double: WorkerDouble) -> FastAPI:
    app = FastAPI()

    @app.post("/inference/v1/dm-narration")
    async def dm_narration(payload: dict[str, Any]) -> JSONResponse:
        double.requests.append(payload)
        if double.status != 200:
            return JSONResponse({"backend": "llm", "detail": "down"}, status_code=double.status)
        body = {
            "session_id": payload["session_id"],
            "narration": NARRATION,
            "sensory_details": SENSORY,
            "suggested_dm_prompts": ["Who rings the bell?"],
            "tension_level": "rising",
            "source": "llm",
        }
        return JSONResponse(body)

    return app


@pytest.fixture
def watcher_app() -> FastAPI:
    """Each test gets an app over an empty whisper log, so proposals never leak between tests."""
    return app_with_container(fresh_store_container())


@pytest.fixture
def worker(monkeypatch: pytest.MonkeyPatch) -> Iterator[WorkerDouble]:
    """Serve the worker double on loopback and point The Watcher at it."""
    double = WorkerDouble()
    with serve(_worker_app(double)) as url:
        double.url = url
        monkeypatch.setenv("RUNEFOBLE_WATCHER_NARRATION_ENGINE", "inference_worker")
        monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", url)
        yield double


@pytest.fixture
def client(watcher_app: FastAPI, worker: WorkerDouble) -> Iterator[TestClient]:
    """Run the real the_watcher lifespan, so the audience narration consumer starts."""
    with TestClient(watcher_app) as test_client:
        assert test_client.get("/healthz").json()["consumers"] == {"the_watcher": "running"}
        yield test_client


def _create_session(campaign_id: str | None = None) -> tuple[str, str]:
    """Bind a new session to a campaign and make DM the table runner through schema tuples."""
    campaign = campaign_id or str(uuid4())
    session_id = str(uuid4())
    asyncio.run(make_table_runner(DM, session_id, campaign))
    return campaign, session_id


def _approved(
    campaign_id: str,
    session_id: str,
    *,
    proposal_id: Any = None,
    approved: bool = True,
    modifier_type: str = "weather_change",
    parameters: dict[str, Any] | None = None,
) -> AudienceModifierApproved:
    return AudienceModifierApproved(
        proposal_id=proposal_id or uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=session_id,
        approved_by=DM,
        approved=approved,
        modifier_type=modifier_type,
        parameters=parameters if parameters is not None else {"weather": "dense fog"},
    )


def _publish(mock_bus: MockAsyncRedis, event: AudienceModifierApproved) -> None:
    async def _send() -> None:
        await RedisStreamsEventBus(client=mock_bus).publish_event(AUDIENCE_STREAM, event)

    asyncio.run(_send())


def _whispers(
    client: TestClient, session_id: str, campaign_id: str, whisper_type: str | None = None
) -> list[dict[str, Any]]:
    params: dict[str, str] = {"session_id": session_id, "campaign_id": campaign_id, "limit": "100"}
    if whisper_type is not None:
        params["whisper_type"] = whisper_type
    res = client.get("/api/v1/watcher/whispers", params=params, headers=bearer(DM))
    assert res.status_code == 200, res.text
    return res.json()["whispers"]


def _narrations(client: TestClient, session_id: str, campaign_id: str) -> list[dict[str, Any]]:
    return _whispers(client, session_id, campaign_id, "audience_narration")


def _unavailable(client: TestClient, session_id: str, campaign_id: str) -> list[dict[str, Any]]:
    return _whispers(client, session_id, campaign_id, "narration_unavailable")


def _dispatched_events(mock_bus: MockAsyncRedis, session_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for _entry_id, fields in mock_bus.streams.get(WATCHER_STREAM, []):
        payload = json.loads(fields["payload"])
        if fields["event_type"] == NARRATIVE_DISPATCHED and payload.get("session_id") == session_id:
            events.append(payload)
    return events


def _barrier(
    mock_bus: MockAsyncRedis, client: TestClient, campaign_id: str, session_id: str
) -> None:
    """Publish one valid approved modifier and wait until its narration is recorded.

    The consumer reads the stream in order, so every earlier message has been handled then.
    """
    proposal = uuid4()
    _publish(mock_bus, _approved(campaign_id, session_id, proposal_id=proposal))
    assert wait_until(
        lambda: any(
            w["metadata"].get("source_proposal_id") == str(proposal)
            for w in _narrations(client, session_id, campaign_id)
        ),
        timeout_s=10.0,
        interval_s=0.05,
    )


def test_approved_modifier_records_one_narration_whisper_for_the_dm(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    proposal = uuid4()

    _publish(
        mock_bus,
        _approved(campaign_id, session_id, proposal_id=proposal, parameters={"weather": "fog"}),
    )

    assert wait_until(
        lambda: len(_narrations(client, session_id, campaign_id)) == 1,
        timeout_s=10.0,
        interval_s=0.05,
    )
    (whisper,) = _narrations(client, session_id, campaign_id)
    assert whisper["content"] == NARRATION
    assert whisper["recipient_role"] == "dungeon_master"
    assert whisper["metadata"]["source_proposal_id"] == str(proposal)
    assert whisper["metadata"]["sensory_details"] == SENSORY
    assert whisper["metadata"]["dispatched"] is False

    # The worker received the campaign, the session and one line that names the modifier.
    (sent,) = worker.requests
    assert sent["campaign_id"] == campaign_id
    assert sent["session_id"] == session_id
    assert any("weather_change" in line for line in sent["recent_events"])
    assert _dispatched_events(mock_bus, session_id) == []


def test_worker_503_records_an_unavailable_notice_and_no_narration(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    worker.status = 503

    _publish(mock_bus, _approved(campaign_id, session_id))

    assert wait_until(
        lambda: len(_unavailable(client, session_id, campaign_id)) == 1,
        timeout_s=10.0,
        interval_s=0.05,
    )
    assert _narrations(client, session_id, campaign_id) == []
    (notice,) = _unavailable(client, session_id, campaign_id)
    assert NARRATION not in notice["content"]
    assert notice["content"].strip()
    assert _dispatched_events(mock_bus, session_id) == []


def test_unreachable_worker_records_an_unavailable_notice(
    watcher_app: FastAPI, mock_bus: MockAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign_id, session_id = _create_session()
    monkeypatch.setenv("RUNEFOBLE_WATCHER_NARRATION_ENGINE", "inference_worker")
    monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", closed_port_url())

    with TestClient(watcher_app) as client:
        _publish(mock_bus, _approved(campaign_id, session_id))
        assert wait_until(
            lambda: len(_unavailable(client, session_id, campaign_id)) == 1,
            timeout_s=10.0,
            interval_s=0.05,
        )
        assert _narrations(client, session_id, campaign_id) == []


def test_vetoed_modifier_and_other_campaign_record_nothing(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    other_campaign, _ = _create_session()

    _publish(mock_bus, _approved(campaign_id, session_id, approved=False))
    _publish(mock_bus, _approved(other_campaign, session_id))
    _barrier(mock_bus, client, campaign_id, session_id)

    assert len(_narrations(client, session_id, campaign_id)) == 1
    assert len(worker.requests) == 1
    # The other-campaign modifier is refused, so it lands on the dead-letter stream once.
    assert len(mock_bus.streams.get(AUDIENCE_DLQ, [])) == 1


def test_redelivered_modifier_records_nothing_new(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    proposal = uuid4()
    event = _approved(campaign_id, session_id, proposal_id=proposal)

    _publish(mock_bus, event)
    _publish(mock_bus, event)
    _barrier(mock_bus, client, campaign_id, session_id)

    mine = [
        w
        for w in _narrations(client, session_id, campaign_id)
        if w["metadata"].get("source_proposal_id") == str(proposal)
    ]
    assert len(mine) == 1
    # The redelivery is refused before the worker runs. Only the proposal and the barrier reach it.
    assert len(worker.requests) == 2


def test_dm_dispatches_the_edited_narration_to_the_table(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    proposal = uuid4()
    _publish(mock_bus, _approved(campaign_id, session_id, proposal_id=proposal))
    assert wait_until(
        lambda: len(_narrations(client, session_id, campaign_id)) == 1,
        timeout_s=10.0,
        interval_s=0.05,
    )
    (whisper,) = _narrations(client, session_id, campaign_id)
    edited = "The bell tolls once. Every torch in the crypt gutters."

    res = client.post(
        f"/api/v1/watcher/whispers/{whisper['whisper_id']}/dispatch",
        json={"session_id": session_id, "campaign_id": campaign_id, "text": edited},
        headers=bearer(DM),
    )

    assert res.status_code == 200, res.text
    assert res.json()["metadata"]["dispatched"] is True
    (event,) = _dispatched_events(mock_bus, session_id)
    assert event["text"] == edited
    assert event["whisper_id"] == whisper["whisper_id"]
    assert event["source_proposal_id"] == str(proposal)
    (after,) = _narrations(client, session_id, campaign_id)
    assert after["metadata"]["dispatched"] is True


def test_dispatch_without_text_sends_the_recorded_narration(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    _publish(mock_bus, _approved(campaign_id, session_id))
    assert wait_until(
        lambda: len(_narrations(client, session_id, campaign_id)) == 1,
        timeout_s=10.0,
        interval_s=0.05,
    )
    (whisper,) = _narrations(client, session_id, campaign_id)

    res = client.post(
        f"/api/v1/watcher/whispers/{whisper['whisper_id']}/dispatch",
        json={"session_id": session_id, "campaign_id": campaign_id},
        headers=bearer(DM),
    )

    assert res.status_code == 200, res.text
    (event,) = _dispatched_events(mock_bus, session_id)
    assert event["text"] == NARRATION


def test_second_dispatch_answers_409_and_publishes_nothing_new(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    _publish(mock_bus, _approved(campaign_id, session_id))
    assert wait_until(
        lambda: len(_narrations(client, session_id, campaign_id)) == 1,
        timeout_s=10.0,
        interval_s=0.05,
    )
    (whisper,) = _narrations(client, session_id, campaign_id)
    url = f"/api/v1/watcher/whispers/{whisper['whisper_id']}/dispatch"
    body = {"session_id": session_id, "campaign_id": campaign_id, "text": "First."}

    assert client.post(url, json=body, headers=bearer(DM)).status_code == 200
    again = client.post(url, json=body, headers=bearer(DM))

    assert again.status_code == 409, again.text
    assert len(_dispatched_events(mock_bus, session_id)) == 1


def test_player_cannot_dispatch_a_narration(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    _publish(mock_bus, _approved(campaign_id, session_id))
    assert wait_until(
        lambda: len(_narrations(client, session_id, campaign_id)) == 1,
        timeout_s=10.0,
        interval_s=0.05,
    )
    (whisper,) = _narrations(client, session_id, campaign_id)

    res = client.post(
        f"/api/v1/watcher/whispers/{whisper['whisper_id']}/dispatch",
        json={"session_id": session_id, "campaign_id": campaign_id, "text": "Leaked."},
        headers=bearer(PLAYER),
    )

    assert res.status_code == 403, res.text
    assert _dispatched_events(mock_bus, session_id) == []


def test_unavailable_notice_cannot_be_dispatched(
    client: TestClient, mock_bus: MockAsyncRedis, worker: WorkerDouble
) -> None:
    campaign_id, session_id = _create_session()
    worker.status = 503
    _publish(mock_bus, _approved(campaign_id, session_id))
    assert wait_until(
        lambda: len(_unavailable(client, session_id, campaign_id)) == 1,
        timeout_s=10.0,
        interval_s=0.05,
    )
    (notice,) = _unavailable(client, session_id, campaign_id)

    res = client.post(
        f"/api/v1/watcher/whispers/{notice['whisper_id']}/dispatch",
        json={"session_id": session_id, "campaign_id": campaign_id, "text": "Anything."},
        headers=bearer(DM),
    )

    assert res.status_code == 409, res.text
    assert _dispatched_events(mock_bus, session_id) == []
