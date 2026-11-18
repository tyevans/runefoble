"""A real HTTP server on 127.0.0.1 that a test drives with a handler function.

It stands in for an external process (Zitadel, the Kubernetes API). Tests use it to check
the exact requests that the production code sends: method, path, headers, and body.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

Reply = tuple[int, Any]
Handler = Callable[["RecordedRequest"], Reply]


@dataclass(frozen=True)
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8")) if self.body else None


@dataclass
class LocalHttpServer:
    handler: Handler
    requests: list[RecordedRequest] = field(default_factory=list)
    _server: ThreadingHTTPServer | None = None
    _thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        assert self._server is not None, "server is not started"
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def start(self) -> LocalHttpServer:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                recorded = RecordedRequest(
                    method=self.command,
                    path=self.path,
                    headers=dict(self.headers.items()),
                    body=self.rfile.read(length) if length else b"",
                )
                owner.requests.append(recorded)
                status, payload = owner.handler(recorded)
                raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            do_GET = _serve
            do_POST = _serve
            do_PUT = _serve
            do_PATCH = _serve

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def __enter__(self) -> LocalHttpServer:
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
