"""Loopback fake of the Zitadel v2 user API for account provisioning tests (ADR-0023).

The fake stands in for the external Zitadel process. It is a true process boundary: the code
under test (`ZitadelAccountProvisioner`) sends real HTTP requests to it over loopback. No client
code is replaced.

It serves the three calls that the provisioner makes:
- `POST /v2beta/users` searches by email,
- `POST /v2beta/users/human` creates a user,
- `POST /v2beta/users/{id}/password_reset` sends a reset link to an existing user.

It records every request body, so a test can check that no password reached Zitadel. A test
sets `fail_status` to make Zitadel answer with that status to every call.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

HUMAN_USER_PATH = "/v2beta/users/human"
SEARCH_PATH = "/v2beta/users"
RESET_SUFFIX = "/password_reset"
STATUS_CONFLICT = 409


@dataclass
class RecordedCall:
    method: str
    path: str
    body: dict[str, Any]
    authorized: bool
    org_header: str | None


@dataclass
class FakeZitadel:
    """The state of one fake. `users` maps a lower-case email to a user id."""

    base_url: str = ""
    expected_token: str = ""
    fail_status: int | None = None
    users: dict[str, str] = field(default_factory=dict)
    calls: list[RecordedCall] = field(default_factory=list)
    _next_id: int = 1000

    def add_existing_user(self, email: str) -> str:
        """Seed a user that already has `email`, as an account made before the invite."""
        return self._new_user(email)

    def calls_to(self, method: str, path: str) -> list[RecordedCall]:
        return [call for call in self.calls if call.method == method and call.path == path]

    def create_calls(self) -> list[RecordedCall]:
        return self.calls_to("POST", HUMAN_USER_PATH)

    def reset_calls(self) -> list[RecordedCall]:
        return [
            call
            for call in self.calls
            if call.method == "POST" and call.path.endswith(RESET_SUFFIX)
        ]

    def _new_user(self, email: str) -> str:
        self._next_id += 1
        user_id = str(self._next_id)
        self.users[email.lower()] = user_id
        return user_id

    def handle(self, method: str, path: str, body: dict[str, Any], headers: Any) -> tuple[int, Any]:
        authorization = headers.get("Authorization", "")
        authorized = authorization == f"Bearer {self.expected_token}"
        self.calls.append(
            RecordedCall(method, path, body, authorized, headers.get("x-zitadel-orgid"))
        )
        if not authorized:
            return 401, {"code": 16, "message": "Errors.Token.Invalid"}
        if self.fail_status is not None:
            return self.fail_status, {"code": 14, "message": "fake Zitadel unavailable"}
        return self._route(method, path, body)

    def _route(self, method: str, path: str, body: dict[str, Any]) -> tuple[int, Any]:
        if method == "POST" and path == SEARCH_PATH:
            # Like Zitadel, the reply has no `result` key when no user matches (protobuf JSON
            # omits an empty list).
            found = self._search(body)
            return 200, ({"result": found, "details": {}} if found else {"details": {}})
        if method == "POST" and path == HUMAN_USER_PATH:
            return self._create(body)
        if method == "POST" and path.endswith(RESET_SUFFIX):
            user_id = path[len("/v2beta/users/") : -len(RESET_SUFFIX)]
            if user_id in self.users.values():
                return 200, {"details": {}}
            return 404, {"code": 5, "message": "User not found"}
        return 404, {"code": 12, "message": "Unknown fake Zitadel route"}

    def _search(self, body: dict[str, Any]) -> list[dict[str, str]]:
        email = _query_email(body)
        user_id = self.users.get(email.lower()) if email else None
        return [{"userId": user_id}] if user_id else []

    def _create(self, body: dict[str, Any]) -> tuple[int, Any]:
        email = str(body.get("email", {}).get("email", ""))
        if email.lower() in self.users:
            return STATUS_CONFLICT, {"code": 6, "message": "User already exists"}
        return 200, {"userId": self._new_user(email), "details": {}}


def _query_email(body: dict[str, Any]) -> str:
    for query in body.get("queries", []):
        email_query = query.get("emailQuery")
        if email_query:
            return str(email_query.get("emailAddress", ""))
    return ""


class _Server(ThreadingHTTPServer):
    def __init__(self, state: FakeZitadel) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.state = state


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) or b"{}"
        try:
            body = json.loads(raw)
        except ValueError:
            body = {}
        state: FakeZitadel = self.server.state  # type: ignore[attr-defined]
        status, document = state.handle(self.command, self.path, body, self.headers)
        payload = json.dumps(document).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return


@contextmanager
def fake_zitadel_server(expected_token: str) -> Iterator[FakeZitadel]:
    """Serve one fake Zitadel API on a free loopback port. Only `expected_token` is accepted."""
    server = _Server(FakeZitadel(expected_token=expected_token))
    server.state.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.state
    finally:
        server.shutdown()
        server.server_close()
