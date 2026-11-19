"""Blackbox tests: the domain error handler maps only domain errors (TASK-0914, ADR-0015).

- A refused domain command (`DomainRefusedError`) answers 400 with its message.
- A missing entity (`DomainNotFoundError`, `AggregateNotFoundError`) answers 404.
- A plain `ValueError` or a `pydantic.ValidationError` from service code is a defect. It
  answers 500 with a fixed text and never sends the exception text to the client.

The board and character cases set up state through public routes. A malformed stored value
comes in at the event store boundary, through the provider frontdoor `set_event_store`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import NoReturn
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from character_sheet.main import app as character_app
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from runefoble_platform.domain_errors import DomainNotFoundError, DomainRefusedError
from runefoble_platform.domain_errors_http import install_domain_error_handlers
from runefoble_platform.event_sourcing import get_event_store, set_event_store

from tests.helpers.ws_identity import bearer

INTERNAL_TEXT = "internal-detail-7f3a"


class _Strict(BaseModel):
    count: int


def _handler_app() -> FastAPI:
    app = FastAPI()
    install_domain_error_handlers(app)

    @app.get("/refused")
    async def refused() -> None:
        raise DomainRefusedError("The token cannot move there")

    @app.get("/missing")
    async def missing() -> None:
        raise DomainNotFoundError("Token 'tok-9' not found on grid")

    @app.get("/missing-aggregate")
    async def missing_aggregate() -> None:
        raise AggregateNotFoundError(uuid4(), "BoardState")

    @app.get("/value-error")
    async def value_error() -> None:
        raise ValueError(INTERNAL_TEXT)

    @app.get("/validation-error")
    async def validation_error() -> None:
        _Strict.model_validate({"count": INTERNAL_TEXT})

    return app


@pytest.fixture
def handler_client() -> TestClient:
    return TestClient(_handler_app(), raise_server_exceptions=False)


def test_a_refused_domain_command_answers_400_with_its_message(handler_client: TestClient):
    res = handler_client.get("/refused")

    assert res.status_code == 400
    assert res.json() == {"detail": "The token cannot move there"}


def test_a_missing_domain_entity_answers_404(handler_client: TestClient):
    res = handler_client.get("/missing")

    assert res.status_code == 404
    assert res.json() == {"detail": "Token 'tok-9' not found on grid"}


def test_a_missing_aggregate_answers_404(handler_client: TestClient):
    assert handler_client.get("/missing-aggregate").status_code == 404


@pytest.mark.parametrize("path", ["/value-error", "/validation-error"])
def test_an_internal_value_error_answers_500_without_its_text(
    handler_client: TestClient, path: str
):
    res = handler_client.get(path)

    assert res.status_code == 500
    assert res.text == "Internal Server Error"
    assert INTERNAL_TEXT not in res.text


class _MalformedStore(InMemoryEventStore):
    """An event store that holds a value that does not parse, as after a bad migration."""

    def read_stream(self, *_args: object, **_kwargs: object) -> NoReturn:  # type: ignore[override]
        raise ValueError(f"malformed stored value: {INTERNAL_TEXT}")


@contextmanager
def _malformed_store() -> Iterator[None]:
    previous = get_event_store()
    set_event_store(_MalformedStore())
    try:
        yield
    finally:
        set_event_store(previous)


def test_a_malformed_board_record_answers_500_without_its_text(board_campaign: str):
    client = TestClient(board_app, headers=bearer("user-test"), raise_server_exceptions=False)
    board_id = f"board-{uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "board_id": board_id, "cols": 10, "rows": 10},
    )
    assert created.status_code == 200, created.text

    with _malformed_store():
        res = client.post(
            f"/api/v1/boards/{board_id}/tokens",
            json={"token_id": "tok-1", "name": "Valeros", "x": 1, "y": 1, "is_friendly": True},
        )

    assert res.status_code == 500
    assert INTERNAL_TEXT not in res.text


def test_a_malformed_character_record_answers_500_without_its_text():
    client = TestClient(character_app, headers=bearer("sheet-owner"), raise_server_exceptions=False)
    created = client.post(
        "/api/v1/characters",
        json={"name": "Merisiel", "character_class": "Rogue", "max_hp": 20},
    )
    assert created.status_code == 200, created.text
    character_id = created.json()["character_id"]

    with _malformed_store():
        res = client.post(
            f"/api/v1/characters/{character_id}/health", json={"delta": -3, "source": "damage"}
        )

    assert res.status_code == 500
    assert INTERNAL_TEXT not in res.text
