"""Shared live stack for restart tests: PostgreSQL, Redis, SpiceDB, and a fake Zitadel (TASK-0698).

A restart test starts each service in a child process with `serve_subprocess`. The child
reads its settings from the environment and reaches the same stores as the test. The stores
are real containers. The issuer is a loopback HTTP server that serves the test signing key
as OIDC discovery and JWKS, so the child verifies tokens over HTTP like a deployed service.

Governed by:
- ADR-0011: the event store is the source of truth
- ADR-0014: frontdoor setup. Writes go through public routes, and the test seeds SpiceDB
  relations through the gRPC write API, as an operator would.
- ADR-0015 (a), (c), (e), (f): no in-process state holds domain facts, every service verifies
  Zitadel tokens itself, and the PostgreSQL event store is mandatory.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.testing.signing_test_issuer import DEFAULT_ISSUER

from tests.helpers.live_services import serve, serve_subprocess
from tests.helpers.ports import free_port
from tests.helpers.redis_container import redis_container
from tests.helpers.spicedb import LiveSpiceDB
from tests.helpers.ws_identity import SIGNING_ISSUER

# (resource_type, resource_id, relation, subject_type, subject_id)
Relationship = tuple[str, str, str, str, str]


def _fake_zitadel_app() -> FastAPI:
    """Serve OIDC discovery and the test JWKS. The verifier rebases the JWKS URL to this origin."""
    app = FastAPI()

    @app.get("/.well-known/openid-configuration")
    def discovery() -> dict[str, str]:
        return {
            "issuer": DEFAULT_ISSUER,
            "jwks_uri": f"{DEFAULT_ISSUER}/.well-known/jwks.json",
        }

    @app.get("/.well-known/jwks.json")
    def jwks() -> dict[str, Any]:
        return SIGNING_ISSUER.jwks()

    return app


def _write_relationships(endpoint: str, token: str, relationships: Sequence[Relationship]) -> None:
    async def write() -> None:
        client = SpiceDBClient(endpoint=endpoint, token=token, insecure=True)
        for resource_type, resource_id, relation, subject_type, subject_id in relationships:
            await client.write_relationship(
                resource_type, resource_id, relation, subject_type, subject_id
            )

    # The gRPC aio client binds to one event loop, so each write runs in its own loop.
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(asyncio.run, write()).result()


@dataclass(frozen=True)
class RestartStack:
    """Endpoints of the shared stores and the fake issuer. Each child process reads them."""

    dsn: str
    redis_url: str
    spicedb: LiveSpiceDB
    zitadel_url: str

    def env(self, **overrides: str) -> dict[str, str]:
        """Return the environment for one child service process."""
        values = {
            "RUNEFOBLE_DATABASE_URL": self.dsn,
            "RUNEFOBLE_EVENT_STORE_BACKEND": "postgresql",
            "RUNEFOBLE_REDIS_URL": self.redis_url,
            "RUNEFOBLE_SPICEDB_ENDPOINT": self.spicedb.endpoint,
            "RUNEFOBLE_SPICEDB_PRESHARED_KEY": self.spicedb.client.token,
            "RUNEFOBLE_ZITADEL_ISSUER": DEFAULT_ISSUER,
            "RUNEFOBLE_ZITADEL_INTERNAL_URL": self.zitadel_url,
            "RUNEFOBLE_ENVIRONMENT": "development",
            **overrides,
        }
        return {key: str(value) for key, value in values.items()}

    def start(
        self, app_path: str, *, crash: bool = False, **overrides: str
    ) -> AbstractContextManager[str]:
        """Start `app_path` in a new child process and yield its base URL until the block ends.

        `crash=True` stops the child with SIGKILL instead of a graceful shutdown.
        """
        return serve_subprocess(app_path, self.env(**overrides), crash=crash)

    def grant(self, relationships: Sequence[Relationship]) -> None:
        """Write SpiceDB relations that the child processes read."""
        _write_relationships(self.spicedb.endpoint, self.spicedb.client.token, relationships)


@pytest.fixture(scope="module")
def restart_stack(postgres_service, live_spicedb_with_schema) -> Iterator[RestartStack]:
    """Start PostgreSQL, Redis, SpiceDB, and the fake issuer for one test module.

    The PostgreSQL and SpiceDB fixtures skip the module when Docker is unavailable.
    """
    with (
        redis_container(free_port()) as redis_url,
        serve(_fake_zitadel_app()) as zitadel_url,
    ):
        yield RestartStack(
            dsn=str(postgres_service["dsn"]),
            redis_url=redis_url,
            spicedb=live_spicedb_with_schema,
            zitadel_url=zitadel_url,
        )
