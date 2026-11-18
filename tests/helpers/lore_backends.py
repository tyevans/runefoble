"""Shared Campaign Lore backends for blackbox tests: an embeddings endpoint and PostgreSQL.

Governed by ADR-0015 (no fallback to fakes in deployed code paths) and Hard Invariant 7.

The OpenAI-compatible embeddings server runs on loopback as its own HTTP process
boundary. It is the only stand-in. The service under test still builds its real
provider, its real pgvector store, and its real start-up probe.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI

from tests.helpers.live_services import serve

LORE_EMBEDDING_MODEL = "test/lore-concept-embed"

# Each word group maps to one vector axis. Words outside the groups share no axis.
LORE_CONCEPT_WORDS: tuple[tuple[str, ...], ...] = (
    ("undead", "zombie", "zombies", "skeleton", "skeletons", "grave", "graves"),
    ("gem", "gems", "vault", "treasure", "jewel"),
)
LORE_EMBEDDING_DIMENSION = len(LORE_CONCEPT_WORDS) + 1

UNDEAD_TITLE = "Sir Gareth and the Sunblade"
VAULT_TITLE = "Vault of the Dragon Eye"
# Each query shares no word with its target document, so only meaning can rank it first.
UNDEAD_QUERY = "zombies skeletons grave"
TREASURE_QUERY = "treasure jewels"
LORE_DOCUMENTS: tuple[tuple[str, str], ...] = (
    (UNDEAD_TITLE, "Sir Gareth wields the Sunblade against undead armies in the crypts."),
    (VAULT_TITLE, "The Dragon Eye gem rests in a secret vault beneath the Citadel."),
)


def concept_vector(text: str) -> list[float]:
    """Return a unit vector that counts each concept group in the text."""
    lowered = text.lower()
    raw = [float(sum(lowered.count(word) for word in words)) for words in LORE_CONCEPT_WORDS]
    raw.append(0.1)  # A constant axis keeps every vector non-zero.
    norm = math.sqrt(sum(value * value for value in raw))
    return [value / norm for value in raw]


def lore_embedding_app() -> FastAPI:
    """An OpenAI-compatible /v1/embeddings endpoint with deterministic concept vectors."""
    app = FastAPI()

    @app.post("/v1/embeddings")
    async def embeddings(payload: dict[str, Any]) -> dict[str, Any]:
        inputs = payload["input"]
        texts = [inputs] if isinstance(inputs, str) else list(inputs)
        return {
            "object": "list",
            "model": payload.get("model", LORE_EMBEDDING_MODEL),
            "data": [
                {"object": "embedding", "index": index, "embedding": concept_vector(text)}
                for index, text in enumerate(texts)
            ],
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        }

    return app


@pytest.fixture(scope="module")
def lore_backends(postgres_service: dict[str, str | int]) -> Iterator[dict[str, str | int]]:
    """Point Campaign Lore at a running embeddings stand-in and the PostgreSQL fixture.

    Campaign Lore has no in-memory vector fallback, so its lifespan needs the PostgreSQL
    fixture. The fixture skips the test when Docker is unavailable.
    """
    with (
        serve(lore_embedding_app()) as embedding_url,
        pytest.MonkeyPatch.context() as env,
    ):
        env.setenv("RUNEFOBLE_DATABASE_URL", str(postgres_service["async_dsn"]))
        env.setenv("RUNEFOBLE_EMBEDDING_BASE_URL", f"{embedding_url}/v1")
        env.setenv("RUNEFOBLE_EMBEDDING_MODEL", LORE_EMBEDDING_MODEL)
        env.setenv("RUNEFOBLE_EMBEDDING_DIMENSION", str(LORE_EMBEDDING_DIMENSION))
        yield postgres_service
