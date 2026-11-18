"""Run a stand-in test double of The Watcher on a real local HTTP port.

The game_session autopilot calls The Watcher over HTTP. The double runs in a
background thread with uvicorn, so the call crosses a real socket. No code
under test is patched.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def serve_watcher_double(app: FastAPI) -> Iterator[str]:
    """Serve `app` on 127.0.0.1 and yield its base URL until the block exits."""
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10.0
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("Watcher test double did not start within 10 seconds")
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10.0)


STAND_IN_ACTION_BODY: dict[str, object] = {
    "character_name": "Kyra",
    "action_type": "attack",
    "action_description": "Kyra lunges at the nearest goblin.",
    "dialogue": "Configured Watcher says hello.",
    "dice_roll_required": "1d20-2",
    "penalties_applied": ["drunk"],
    "source": "llm",
}


def watcher_stand_in_app(
    *, status_code: int = 200, body: dict[str, object] | None = None
) -> FastAPI:
    """Build a Watcher double that answers the stand-in route with a fixed status and body."""
    app = FastAPI()
    reply = STAND_IN_ACTION_BODY if body is None else body

    @app.post("/api/v1/watcher/stand-in/act")
    async def stand_in_act(payload: dict[str, object]) -> JSONResponse:
        return JSONResponse(status_code=status_code, content=reply)

    return app
