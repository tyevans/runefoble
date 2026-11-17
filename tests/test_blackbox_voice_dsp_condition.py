"""Blackbox tests for the voice_agent speech conditioning route (TASK-0675).

POST /api/v1/voice/dsp/condition returns conditioned text and DSP parameters.
It never returns audio. Tests use the public HTTP route only.
"""

from fastapi.testclient import TestClient
from voice_agent.main import app

SPEECH = "I can drink the whole tavern under the table!"


def test_condition_returns_drunk_text_and_dsp_config() -> None:
    client = TestClient(app)

    res = client.post("/api/v1/voice/dsp/condition", json={"text": SPEECH, "filters": ["drunk"]})

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["original_text"] == SPEECH
    assert body["conditioned_text"] != SPEECH
    assert body["active_filters"] == ["drunk"]
    assert body["dsp_config"]["slur_intensity"] == 0.8
    assert "audio_base64" not in body


def test_condition_without_filters_returns_text_unchanged() -> None:
    client = TestClient(app)

    res = client.post("/api/v1/voice/dsp/condition", json={"text": SPEECH, "filters": []})

    assert res.status_code == 200, res.text
    assert res.json()["conditioned_text"] == SPEECH


def test_condition_rejects_empty_text() -> None:
    client = TestClient(app)

    res = client.post("/api/v1/voice/dsp/condition", json={"text": "", "filters": ["drunk"]})

    assert res.status_code == 422
