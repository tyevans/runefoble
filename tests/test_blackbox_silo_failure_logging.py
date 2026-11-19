"""Blackbox suite for TASK-0924: a Silo failure that becomes HTTP 503 is logged.

Each route answers 503 when Silo refuses a request. The service then writes one error log
record that names the bucket and the object key. The record never holds the object bytes or
the Silo credentials (ADR-0015). Setup uses the public routes and the Silo HTTP boundary
(FakeSilo) only.
"""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

import pytest
from asset_forge.main import app as asset_forge_app
from board_state.main import app as board_app
from fastapi.testclient import TestClient

from tests.helpers.silo_fixtures import (
    PNG_SAMPLE_BYTES,
    SILO_TEST_ACCESS_KEY,
    SILO_TEST_SECRET_KEY,
    FakeSilo,
)
from tests.helpers.ws_identity import bearer
from tests.test_blackbox_uvtt_import.conftest import build_sample_dd2vtt_dict

ASSET_BUCKET = "runefoble-assets"
SILO_REFUSES_WRITE = 403


@pytest.fixture
def forge_campaign(spicedb) -> str:
    """A campaign with one player. Asset forge takes a UUID campaign id."""
    campaign_id = str(uuid4())
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="player",
            subject_type="user",
            subject_id="forge-tester",
        )
    )
    return campaign_id


@pytest.fixture
def forge_client() -> TestClient:
    return TestClient(asset_forge_app, headers=bearer("forge-tester"))


def _silo_error_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno == logging.ERROR and "Silo" in r.getMessage()]


def _assert_logged_failure(caplog: pytest.LogCaptureFixture, key_prefix: str) -> None:
    records = _silo_error_records(caplog)
    assert records, "expected an error log record for the Silo failure"
    message = records[-1].getMessage()
    assert f"bucket={ASSET_BUCKET}" in message, message
    assert f"object_key={key_prefix}" in message, message
    assert str(SILO_REFUSES_WRITE) in message, message

    full_log = "\n".join(r.getMessage() for r in caplog.records)
    assert SILO_TEST_SECRET_KEY not in full_log
    assert SILO_TEST_ACCESS_KEY not in full_log
    assert repr(PNG_SAMPLE_BYTES) not in full_log
    assert "IHDR" not in full_log


def test_battlemap_forge_logs_the_refused_silo_write(
    forge_client: TestClient,
    silo_double: FakeSilo,
    forge_campaign: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    silo_double.forced_status = SILO_REFUSES_WRITE
    caplog.set_level(logging.ERROR)

    response = forge_client.post(
        "/api/v1/forge/battlemap",
        json={
            "prompt": "Sunken crypt",
            "width_cells": 8,
            "height_cells": 8,
            "campaign_id": forge_campaign,
        },
    )

    assert response.status_code == 503, response.text
    _assert_logged_failure(caplog, "battlemaps/")


def test_asset_upload_logs_the_refused_silo_write(
    forge_client: TestClient, silo_double: FakeSilo, caplog: pytest.LogCaptureFixture
) -> None:
    silo_double.forced_status = SILO_REFUSES_WRITE
    caplog.set_level(logging.ERROR)

    response = forge_client.post(
        "/api/v1/assets/upload",
        files={"file": ("crest.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"asset_type": "avatar"},
    )

    assert response.status_code == 503, response.text
    _assert_logged_failure(caplog, "avatars/")


def test_asset_read_logs_the_refused_silo_read(
    forge_client: TestClient, silo_double: FakeSilo, caplog: pytest.LogCaptureFixture
) -> None:
    created = forge_client.post(
        "/api/v1/assets/upload",
        files={"file": ("crest.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"asset_type": "avatar"},
    )
    assert created.status_code == 200, created.text
    silo_double.forced_status = SILO_REFUSES_WRITE
    caplog.set_level(logging.ERROR)

    response = forge_client.get(f"/api/v1/assets/{created.json()['asset_id']}/stream")

    assert response.status_code == 503, response.text
    _assert_logged_failure(caplog, "avatars/")


def test_asset_delete_logs_the_refused_silo_delete(
    forge_client: TestClient, silo_double: FakeSilo, caplog: pytest.LogCaptureFixture
) -> None:
    created = forge_client.post(
        "/api/v1/assets/upload",
        files={"file": ("crest.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"asset_type": "avatar"},
    )
    assert created.status_code == 200, created.text
    silo_double.forced_status = SILO_REFUSES_WRITE
    caplog.set_level(logging.ERROR)

    response = forge_client.delete(f"/api/v1/assets/{created.json()['asset_id']}")

    assert response.status_code == 503, response.text
    _assert_logged_failure(caplog, "avatars/")


def test_uvtt_import_logs_the_refused_silo_write(
    board_campaign: str, silo_double: FakeSilo, caplog: pytest.LogCaptureFixture
) -> None:
    client = TestClient(board_app, headers=bearer("user-test"))
    board_id = f"camp-uvtt-{uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "session_id": board_id, "cols": 4, "rows": 4},
    )
    assert created.status_code == 200, created.text
    silo_double.forced_status = SILO_REFUSES_WRITE
    caplog.set_level(logging.ERROR)

    response = client.post(
        f"/api/v1/boards/{board_id}/import/uvtt",
        files={
            "file": (
                "crypt.dd2vtt",
                json.dumps(build_sample_dd2vtt_dict()).encode(),
                "application/json",
            )
        },
    )

    assert response.status_code == 503, response.text
    _assert_logged_failure(caplog, "battlemaps/")
