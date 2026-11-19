"""Gateway API test configuration.

The gateway tests run from `gateway/api` (`uv run pytest gateway/api`). They use the same test-mode
settings as the root `tests/conftest.py`, so a test gets the same environment in both runs.
"""

import os

from runefoble_platform.service_client import OWNER_URL_FIELDS

# Test mode: the SpiceDB preshared key has no default outside tests.
os.environ.setdefault("RUNEFOBLE_SPICEDB_PRESHARED_KEY", "test-only-spicedb-key")
# Service URLs have no code defaults. Unless a test sets one itself, each owner points at a closed
# loopback port, so no test reaches a real service by accident.
for _service in OWNER_URL_FIELDS:
    os.environ.setdefault("RUNEFOBLE_" + OWNER_URL_FIELDS[_service].upper(), "http://127.0.0.1:9")
os.environ.setdefault("RUNEFOBLE_SERVICE_CREDENTIAL", "test-only-service-credential")
# Tests select the in-memory event store explicitly (TASK-0707).
os.environ["RUNEFOBLE_EVENT_STORE_BACKEND"] = "memory"
os.environ.setdefault("RUNEFOBLE_WATCHER_ENGINE", "heuristic")

# The same shared fixtures as the root conftest. Gateway tests use the service harness, the
# owner doubles, the Silo double (autouse), and the identity fixtures.
pytest_plugins = [
    "tests.realtime_session",
    "tests.helpers.audio_synth",
    "tests.helpers.campaign_analytics_service",
    "tests.helpers.event_store_seam",
    "tests.helpers.lore_backends",
    "tests.helpers.module_state",
    "tests.helpers.postgres",
    "tests.helpers.prd_fixtures",
    "tests.helpers.restart_stack",
    "tests.helpers.service_harness",
    "tests.helpers.silo_fixtures",
    "tests.helpers.spectator_table",
    "tests.helpers.spicedb",
    "tests.helpers.stand_in_policy",
    "tests.helpers.voice_identity",
    "tests.helpers.voice_signaling",
    "tests.helpers.zitadel_auth",
]
