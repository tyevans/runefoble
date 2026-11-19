"""Blackbox test: a combat end in game_session reaches soundscape over one real Redis (TASK-0803).

game_session and soundscape run as child processes. Both use one Redis container, one
PostgreSQL event store, one SpiceDB, and one fake Zitadel issuer, from the `restart_stack`
fixture. Each child gets its own free port. The test drives game_session only through public
routes, and it reads the soundscape tension route only. It never touches a Redis stream or a
private seam.

Governed by:
- ADR-0006: Redis Streams domain event streaming
- ADR-0007: Domain-driven design architecture
- ADR-0014: BDD and blackbox frontdoor tests
- AGENTS.md Hard Invariant 7: setup through frontdoors, assertions on public projections
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest

from tests.helpers.live_services import serve_subprocesses
from tests.helpers.polling import wait_until
from tests.helpers.restart_stack import RestartStack
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.docker

GAME_SESSION_APP = "game_session.main:app"
SOUNDSCAPE_APP = "soundscape.main:app"

REQUEST_TIMEOUT_SECONDS = 30.0
# The consumer reads the stream on its own loop, so the change arrives after the POST returns.
PROPAGATION_DEADLINE_SECONDS = 30.0
POLL_INTERVAL_SECONDS = 0.2

# A combat encounter with one CR 2 enemy at full health scores 55 (40 base + 5 round + 10 CR).
# That score falls in the "tension" band. Ending combat returns the ambient score of 10.
COMBAT_TENSION_SCORE = 55
AMBIENT_TENSION_SCORE = 10


@pytest.fixture
def live_pair(restart_stack: RestartStack) -> Iterator[dict[str, str]]:
    """Start game_session and soundscape as child processes on the shared live stack."""
    with serve_subprocesses(
        {"game_session": GAME_SESSION_APP, "soundscape": SOUNDSCAPE_APP},
        restart_stack.env(),
    ) as urls:
        yield urls


def _headers(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def _post(
    url: str, *, headers: dict[str, str], json: dict[str, Any] | None = None
) -> httpx.Response:
    return httpx.post(url, json=json, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)


def _tension(base: str, session_id: str, headers: dict[str, str]) -> dict[str, Any]:
    response = httpx.get(
        f"{base}/api/v1/soundscape/tension",
        params={"session_id": session_id},
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _wait_until(
    read: Callable[[], dict[str, Any]], done: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    """Poll `read` until `done` holds. Fail with the last reading when the deadline passes."""
    state: dict[str, Any] = {}

    def reached() -> bool:
        state.update(read())
        return done(state)

    if not wait_until(
        reached, timeout_s=PROPAGATION_DEADLINE_SECONDS, interval_s=POLL_INTERVAL_SECONDS
    ):
        raise AssertionError(f"soundscape did not reach the expected state; last read: {state}")
    return state


def test_combat_end_on_game_session_returns_soundscape_tension_to_ambient(
    restart_stack: RestartStack, live_pair: dict[str, str]
) -> None:
    """Ending combat through game_session clears the combat tension that soundscape holds."""
    game_session, soundscape = live_pair["game_session"], live_pair["soundscape"]
    dm = f"dm_{uuid4().hex[:8]}"
    headers = _headers(dm)

    campaign = _post(
        f"{game_session}/api/v1/campaigns", headers=headers, json={"title": "Ash Warrens"}
    )
    assert campaign.status_code in (200, 201), campaign.text
    created = _post(
        f"{game_session}/api/v1/campaigns/{campaign.json()['id']}/sessions",
        headers=headers,
        json={"title": "Ash Warrens Session 1"},
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    started = _post(f"{game_session}/api/v1/sessions/{session_id}/start", headers=headers)
    assert started.status_code == 200, started.text

    combat = _post(
        f"{game_session}/api/v1/sessions/{session_id}/combat/start",
        headers=headers,
        json={"combatants": [{"combatant_id": "orc-1", "name": "Orc", "cr": 2.0}]},
    )
    assert combat.status_code == 200, combat.text
    in_combat = _wait_until(
        lambda: _tension(soundscape, session_id, headers),
        lambda state: state["tension_score"] == COMBAT_TENSION_SCORE,
    )
    assert in_combat["stem_profile"] == "tension"

    ended = _post(f"{game_session}/api/v1/sessions/{session_id}/combat/end", headers=headers)
    assert ended.status_code == 200, ended.text
    after_end = _wait_until(
        lambda: _tension(soundscape, session_id, headers),
        lambda state: state["tension_score"] == AMBIENT_TENSION_SCORE,
    )
    assert after_end["stem_profile"] == "exploration"
