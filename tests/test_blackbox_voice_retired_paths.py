"""Blackbox tests: retired voice routes are not served (DoR 9, TASK-0494).

Every voice-agent HTTP route lives under /api/v1/voice. The unprefixed aliases and the
duplicate TTS path were removed, so each one returns 404 through the public HTTP frontdoor.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from voice_agent.main import app

RETIRED_ROUTES: list[tuple[str, str, dict | None]] = [
    ("POST", "/api/v1/voice/tts", {"text": "Hello", "persona_id": "watcher_dm"}),
    ("GET", "/voice/presets", None),
    ("POST", "/voice/modulate", {"session_id": "session-x", "peer_id": "peer-x"}),
    ("POST", "/voice/filters/barge-in/evaluate", {}),
    ("POST", "/voice/aec/benchmark", {}),
    ("GET", "/voice/streams/session-x/quality", None),
    ("POST", "/voice/streams/session-x/report", {}),
    ("POST", "/voice/streams/session-x/quality", {}),
]


@pytest.mark.parametrize(("method", "url", "body"), RETIRED_ROUTES)
def test_retired_voice_route_returns_404(method: str, url: str, body: dict | None) -> None:
    client = TestClient(app)

    resp = client.request(method, url, json=body)

    assert resp.status_code == 404, resp.text
