"""Blackbox start-up tests: Audience Studio has no in-memory store and no mock stream bus.

Governed by:
- TASK-0724: production code cannot select in-memory adapters.
- ADR-0015 decision f: a deployed process never runs on memory.
- Hard Invariant 7: the built service is started as a process. Only its exit code and
  stderr are read.

The helper sets NODE_ENV=test, so each case also proves that NODE_ENV does not open a memory path.
"""

from __future__ import annotations

import pytest

from tests.helpers.audience_server import AudienceStudioProcess

DATABASE_URL = "postgresql://runefoble:secret@127.0.0.1:9/runefoble"
REDIS_URL = "redis://127.0.0.1:9/0"
SPICEDB = {
    "RUNEFOBLE_SPICEDB_ENDPOINT": "127.0.0.1:9",
    "RUNEFOBLE_SPICEDB_PRESHARED_KEY": "test-only",
}


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"RUNEFOBLE_REDIS_URL": REDIS_URL}, "RUNEFOBLE_DATABASE_URL is not set"),
        ({"RUNEFOBLE_DATABASE_URL": DATABASE_URL}, "RUNEFOBLE_REDIS_URL is not set"),
        (
            {"RUNEFOBLE_DATABASE_URL": DATABASE_URL, "RUNEFOBLE_REDIS_URL": "mock://redis"},
            "RUNEFOBLE_REDIS_URL must start with redis:// or rediss://",
        ),
        (
            {
                "RUNEFOBLE_EVENT_STORE_BACKEND": "memory",
                "RUNEFOBLE_DATABASE_URL": DATABASE_URL,
                "RUNEFOBLE_REDIS_URL": REDIS_URL,
            },
            'RUNEFOBLE_EVENT_STORE_BACKEND must be "postgresql"',
        ),
    ],
    ids=["no-database", "no-redis", "mock-redis", "memory-backend"],
)
def test_the_service_refuses_to_start_without_real_stores(env: dict[str, str], message: str):
    """The process exits with an error that names the missing or refused setting."""
    process = AudienceStudioProcess({**SPICEDB, **env})
    process.start(wait_healthy=False)
    try:
        code, stderr = process.wait_for_exit(timeout=60.0)
    finally:
        process.stop()
    assert code != 0
    assert message in stderr
