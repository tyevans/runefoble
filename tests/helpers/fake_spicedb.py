"""A small SpiceDB stand-in for Audience Studio blackbox tests.

SpiceDB is an external process. The service calls two of its HTTP routes:
`/v1/permissions/check` and, in tests only, `/v1/relationships/write` for setup. This fake
serves both. It implements the part of `libs/runefoble_auth/schema/runefoble.zed` that the
service uses: `run_session` is granted to owner, dungeon_master, and game_master.
Tests grant relations through the write route, the same way they would reach SpiceDB.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx

RUN_SESSION_RELATIONS = frozenset({"owner", "dungeon_master", "game_master"})
HAS_PERMISSION = "PERMISSIONSHIP_HAS_PERMISSION"
NO_PERMISSION = "PERMISSIONSHIP_NO_PERMISSION"


class FakeSpiceDB:
    """Serves SpiceDB's HTTP API on 127.0.0.1 until stopped."""

    def __init__(self) -> None:
        self._tuples: set[tuple[str, str, str, str]] = set()
        self._lock = threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - http.server naming
                length = int(self.headers.get("Content-Length", "0"))
                body: dict[str, Any] = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/v1/relationships/write":
                    fake._write(body)
                    reply: dict[str, Any] = {}
                elif self.path == "/v1/permissions/check":
                    reply = {"permissionship": fake._check(body)}
                else:
                    self.send_error(404)
                    return
                payload = json.dumps(reply).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def grant(self, campaign_id: str, relation: str, user_id: str) -> None:
        """Write one relationship through the SpiceDB write route."""
        res = httpx.post(
            f"{self.url}/v1/relationships/write",
            json={
                "updates": [
                    {
                        "operation": "OPERATION_TOUCH",
                        "relationship": {
                            "resource": {"objectType": "campaign", "objectId": campaign_id},
                            "relation": relation,
                            "subject": {"object": {"objectType": "user", "objectId": user_id}},
                        },
                    }
                ]
            },
        )
        res.raise_for_status()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def _write(self, body: dict[str, Any]) -> None:
        with self._lock:
            for update in body.get("updates", []):
                rel = update["relationship"]
                self._tuples.add(
                    (
                        rel["resource"]["objectId"],
                        rel["relation"],
                        rel["subject"]["object"]["objectId"],
                        rel["resource"]["objectType"],
                    )
                )

    def _check(self, body: dict[str, Any]) -> str:
        resource = body["resource"]
        subject = body["subject"]["object"]["objectId"]
        relations = (
            RUN_SESSION_RELATIONS if body["permission"] == "run_session" else {body["permission"]}
        )
        with self._lock:
            granted = any(
                (resource["objectId"], rel, subject, resource["objectType"]) in self._tuples
                for rel in relations
            )
        return HAS_PERMISSION if granted else NO_PERMISSION
