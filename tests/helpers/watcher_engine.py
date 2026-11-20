"""Select The Watcher's engine through its public settings in a blackbox test."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def select_worker_engine(monkeypatch: pytest.MonkeyPatch, worker_url: str | None) -> None:
    """Make every Watcher port call the inference worker at `worker_url`. None leaves the URL unset.

    The intent port still parses with the grammar first (ADR-0022 a), so a test that needs the
    worker for speech must send a transcript that the grammar returns as `narrative`.
    """
    monkeypatch.setenv("RUNEFOBLE_WATCHER_INTENT_ENGINE", "inference_worker")
    monkeypatch.setenv("RUNEFOBLE_WATCHER_STAND_IN_ENGINE", "inference_worker")
    monkeypatch.setenv("RUNEFOBLE_WATCHER_NARRATION_ENGINE", "inference_worker")
    if worker_url is None:
        monkeypatch.delenv("RUNEFOBLE_INFERENCE_URL", raising=False)
    else:
        monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", worker_url)


def error_fields(detail: dict[str, Any]) -> dict[str, Any]:
    """Return the stable error fields of a 503 body. The free-text `message` is not part of them."""
    return {key: value for key, value in detail.items() if key != "message"}


def stand_in_worker_double() -> FastAPI:
    """A loopback inference worker that answers stand-in calls in the published worker contract.

    The worker is the process boundary here. Its reply fields are the ones
    `the_watcher/adapters/worker_engines.py` reads. The reply echoes the requested character.
    """
    app = FastAPI()

    @app.post("/inference/v1/stand-in-action")
    async def _stand_in(request: Request) -> JSONResponse:
        payload = await request.json()
        return JSONResponse(
            {
                "character_name": payload["character_name"],
                "action_type": "attack",
                "narrative_flavor": f"{payload['character_name']} lunges at the nearest goblin.",
                "dialogue": "Hic! Onward!",
                "penalties_applied": payload.get("penalties", []),
                "guardrails_applied": [],
                "source": "llm",
            }
        )

    return app
