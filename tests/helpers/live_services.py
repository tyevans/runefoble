"""Run owning services as real HTTP servers in this process for gateway blackbox tests.

The services run under uvicorn on loopback ports. Gateway tools reach them over
HTTP, exactly as they do in a deployed cluster. Nothing patches the HTTP client.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def serve(app: FastAPI, *, lifespan: Literal["on", "off"] = "off") -> Iterator[str]:
    """Serve an ASGI app on a free loopback port and yield its base URL.

    Pass `lifespan="on"` for a service that builds its state at start-up.
    """
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan=lifespan)
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10.0
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError(f"uvicorn failed to start on port {port}")
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10.0)


def unavailable_app(status_code: int = 503) -> FastAPI:
    """Return an upstream stand-in that answers every route with the given status."""
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def _down(path: str) -> JSONResponse:
        return JSONResponse({"detail": "service maintenance"}, status_code=status_code)

    return app


def closed_port_url() -> str:
    """Return a base URL where nothing listens, so connections are refused."""
    return f"http://127.0.0.1:{_free_port()}"
