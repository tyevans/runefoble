"""Child process for the Soundscape restart test (TASK-0576).

The parent test writes through the public routes, then starts this module in a new
Python process on the same PostgreSQL event store. The child reads through the public
tension route only. It prints one JSON line on stdout.

Usage: python tests/helpers/soundscape_restart_child.py <dsn> <session_id> [aggregate]
With the `aggregate` flag the child also prints the soundscape aggregate id it derives.
"""

from __future__ import annotations

import json
import sys

from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import build_event_store, set_event_store


def main() -> None:
    dsn, session_id = sys.argv[1], sys.argv[2]
    set_event_store(
        build_event_store(PlatformSettings(database_url=dsn, event_store_backend="postgresql"))
    )

    from fastapi.testclient import TestClient
    from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
    from soundscape.dependencies import set_zitadel_auth_service
    from soundscape.main import app

    issuer = SigningTestIssuer()
    set_zitadel_auth_service(issuer.verifier())
    client = TestClient(app, headers={"Authorization": f"Bearer {issuer.mint('restart-reader')}"})
    response = client.get("/api/v1/soundscape/tension", params={"session_id": session_id})
    report: dict[str, object] = {"status": response.status_code, "body": response.json()}
    if len(sys.argv) > 3 and sys.argv[3] == "aggregate":
        from soundscape.ids import soundscape_aggregate_id

        report["aggregate_id"] = str(soundscape_aggregate_id(session_id))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
