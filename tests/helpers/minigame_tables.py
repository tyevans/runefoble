"""Opens minigame tables through the public HTTP route for blackbox tests (TASK-0566)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers.game_session_app import session_app
from tests.helpers.ws_identity import SIGNING_ISSUER


def open_minigame_table(
    table_id: str,
    *,
    establishment_id: str = "est-default",
    game_type: str = "darts",
    user_id: str = "minigame-tester",
) -> None:
    """POST the table open command as a patron of the establishment."""
    client = TestClient(session_app)
    res = client.post(
        "/api/v1/tavern/tables",
        json={
            "table_id": table_id,
            "establishment_id": establishment_id,
            "game_type": game_type,
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(user_id)}"},
    )
    assert res.status_code == 201, res.text
