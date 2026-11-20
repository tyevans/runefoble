"""Run owning services as real HTTP servers in this process for gateway blackbox tests.

The services run under uvicorn on loopback ports. Gateway tools reach them over
HTTP, exactly as they do in a deployed cluster. Nothing patches the HTTP client.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import ExitStack, contextmanager
from typing import IO, Literal

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from tests.helpers.polling import wait_until
from tests.helpers.ports import free_port


@contextmanager
def serve(app: FastAPI, *, lifespan: Literal["on", "off"] = "off") -> Iterator[str]:
    """Serve an ASGI app on a free loopback port and yield its base URL.

    Pass `lifespan="on"` for a service that builds its state at start-up.
    """
    port = free_port()
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


@contextmanager
def serve_subprocess(
    app_path: str, env: Mapping[str, str], *, crash: bool = False
) -> Iterator[str]:
    """Run an ASGI app in a child uvicorn process on a loopback port and yield its base URL.

    `app_path` is an import path such as `game_session.main:app`. The child inherits this
    process environment, and `env` overrides it. The child shares no memory with the test,
    so a restart test starts a second child over the same stores. The child is stopped when
    the block exits, also when the block raises. A child that exits before it listens raises
    RuntimeError with its log output.

    By default the child gets SIGTERM and shuts down gracefully. Graceful shutdown closes open
    WebSockets, and the service records each close as a disconnect. Pass `crash=True` to send
    SIGKILL. A crash runs no shutdown code, so only state that was already saved survives.
    """
    port = free_port()
    with tempfile.TemporaryFile(mode="w+") as log:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                app_path,
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            env={**os.environ, **env},
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_for_listener(proc, port, log)
            yield f"http://127.0.0.1:{port}"
        finally:
            _stop_process(proc, crash=crash)


@contextmanager
def serve_subprocesses(apps: Mapping[str, str], env: Mapping[str, str]) -> Iterator[dict[str, str]]:
    """Run several ASGI apps as child processes that share one environment.

    `apps` maps a service name to its import path. The result maps the same names to base URLs.
    Each child gets its own free port, and each one is stopped when the block exits. An
    exit stops the children that already started, also when a later child fails to start.
    """
    with ExitStack() as stack:
        urls = {
            name: stack.enter_context(serve_subprocess(path, env)) for name, path in apps.items()
        }
        yield urls


def _wait_for_listener(proc: subprocess.Popen[bytes], port: int, log: IO[str]) -> None:
    def listening() -> bool:
        if proc.poll() is not None:
            raise RuntimeError(f"service exited with {proc.returncode}: {_read_log(log)}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            return False

    if not wait_until(listening, timeout_s=60.0, interval_s=0.05):
        raise RuntimeError(f"service did not listen on port {port}: {_read_log(log)}")


def _read_log(log: IO[str]) -> str:
    log.seek(0)
    return log.read()[-4000:]


def _stop_process(proc: subprocess.Popen[bytes], *, crash: bool) -> None:
    if proc.poll() is not None:
        return
    if crash:
        proc.kill()
        proc.wait(timeout=10.0)
        return
    proc.terminate()
    try:
        proc.wait(timeout=15.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10.0)


def unavailable_app(status_code: int = 503) -> FastAPI:
    """Return an upstream stand-in that answers every route with the given status."""
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def _down(path: str) -> JSONResponse:
        return JSONResponse({"detail": "service maintenance"}, status_code=status_code)

    return app


def closed_port_url() -> str:
    """Return a base URL where nothing listens, so connections are refused."""
    return f"http://127.0.0.1:{free_port()}"


@contextmanager
def unanswered_port_url() -> Iterator[str]:
    """Yield a base URL where a TCP connect never completes.

    This is the state of a Kubernetes Service that still routes to a deleted pod: the SYN
    gets no answer. The listener has a backlog of 0 and never accepts. Other connections
    fill its accept queue, so the kernel drops each new SYN, and the connect waits.
    """
    with ExitStack() as stack:
        listener = stack.enter_context(socket.socket())
        listener.bind(("127.0.0.1", 0))
        listener.listen(0)
        port = listener.getsockname()[1]
        for _ in range(4):
            filler = stack.enter_context(socket.socket())
            filler.setblocking(False)
            filler.connect_ex(("127.0.0.1", port))
        yield f"http://127.0.0.1:{port}"
