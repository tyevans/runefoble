"""Blackbox tests for the Rules Compendium retrieval mode (TASK-0616).

Governed by Hard Invariant 7. Every test configures the service through its
environment settings, starts it through its lifespan, and calls its public
REST search route. The only stand-in is an OpenAI-compatible embeddings server
that runs as a separate HTTP process on loopback. That server is an external
process boundary, so it is the one permitted double.
"""

import math
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rules_compendium.main import create_app

from tests.helpers.live_services import serve
from tests.helpers.ws_identity import bearer

SEARCH_PATH = "/api/v1/compendium/rules/search"

# A paraphrase of Fireball that shares no word with its SRD entry.
PARAPHRASE_QUERY = "magical blaze that burns creatures"

# The test embedding model maps these word groups to vector axes.
CONCEPT_WORDS: tuple[tuple[str, ...], ...] = (
    ("blaze", "fire", "burn", "flame"),
    ("sleep", "slumber"),
    ("heal", "mend"),
)
TEST_EMBEDDING_DIMENSION = len(CONCEPT_WORDS) + 1


def _concept_vector(text: str) -> list[float]:
    lowered = text.lower()
    raw = [float(sum(lowered.count(word) for word in words)) for words in CONCEPT_WORDS]
    raw.append(0.1)  # A constant axis keeps every vector non-zero.
    norm = math.sqrt(sum(value * value for value in raw))
    return [value / norm for value in raw]


def _embedding_server_app() -> FastAPI:
    """An OpenAI-compatible /v1/embeddings endpoint with deterministic concept vectors."""
    app = FastAPI()

    @app.post("/v1/embeddings")
    async def embeddings(payload: dict[str, Any]) -> dict[str, Any]:
        inputs = payload["input"]
        texts = [inputs] if isinstance(inputs, str) else list(inputs)
        return {
            "object": "list",
            "model": payload.get("model", "test/concept-embed"),
            "data": [
                {"object": "embedding", "index": index, "embedding": _concept_vector(text)}
                for index, text in enumerate(texts)
            ],
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        }

    return app


def _result_names(body: dict[str, Any]) -> list[str]:
    return [result["name"] for result in body["results"]]


def test_search_reports_lexical_mode_when_no_provider_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RUNEFOBLE_RULES_EMBEDDING", raising=False)

    with TestClient(create_app(), headers=bearer("user-test")) as client:
        resp = client.get(SEARCH_PATH, params={"query": "Fireball"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["retrieval_mode"] == "lexical"
    assert "Fireball" in _result_names(body)


def test_lexical_mode_does_not_match_a_paraphrase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUNEFOBLE_RULES_EMBEDDING", raising=False)

    with TestClient(create_app(), headers=bearer("user-test")) as client:
        resp = client.get(SEARCH_PATH, params={"query": PARAPHRASE_QUERY})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["retrieval_mode"] == "lexical"
    assert "Fireball" not in _result_names(body)


def test_configured_provider_finds_a_paraphrase(monkeypatch: pytest.MonkeyPatch) -> None:
    with serve(_embedding_server_app()) as embedding_url:
        monkeypatch.setenv("RUNEFOBLE_RULES_EMBEDDING", "openai_compatible")
        monkeypatch.setenv("RUNEFOBLE_EMBEDDING_BASE_URL", f"{embedding_url}/v1")
        monkeypatch.setenv("RUNEFOBLE_EMBEDDING_MODEL", "test/concept-embed")
        monkeypatch.setenv("RUNEFOBLE_EMBEDDING_DIMENSION", str(TEST_EMBEDDING_DIMENSION))

        with TestClient(create_app(), headers=bearer("user-test")) as client:
            resp = client.get(SEARCH_PATH, params={"query": PARAPHRASE_QUERY})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["retrieval_mode"] == "hybrid"
    assert "Fireball" in _result_names(body)


def test_openai_compatible_mode_refuses_to_start_without_an_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNEFOBLE_RULES_EMBEDDING", "openai_compatible")
    monkeypatch.delenv("RUNEFOBLE_EMBEDDING_BASE_URL", raising=False)
    monkeypatch.setenv("RUNEFOBLE_EMBEDDING_MODEL", "test/concept-embed")
    monkeypatch.setenv("RUNEFOBLE_EMBEDDING_DIMENSION", str(TEST_EMBEDDING_DIMENSION))

    with (
        pytest.raises(ValueError, match="RUNEFOBLE_EMBEDDING_BASE_URL"),
        TestClient(create_app(), headers=bearer("user-test")),
    ):
        pass
