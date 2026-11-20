"""A loopback owner whose pooled keep-alive connections go stale after the first reply.

This is the state of the gateway pool right after an owner restart: the gateway holds an
idle keep-alive connection, sends the next request on it, and the connection closes before
any response arrives. The client sees `httpx.RemoteProtocolError`.

The owner is a raw TCP server, not a FastAPI app, because uvicorn always answers a request
that it has read. Each connection answers its first request with `200` and stays open. When a
second request arrives on the same connection, the owner reads it and closes the connection
without an answer. A new connection always gets an answer.
"""

from __future__ import annotations

import json
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class StaleConnectionOwner:
    """The base URL of the owner, and each request line that it read, in order."""

    base_url: str
    received: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


def _read_request(conn: socket.socket, buffer: bytearray) -> str | None:
    """Read one HTTP/1.1 request from the connection. Return its request line, or None at EOF."""
    while b"\r\n\r\n" not in buffer:
        chunk = conn.recv(65536)
        if not chunk:
            return None
        buffer.extend(chunk)
    head, _, rest = bytes(buffer).partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    length = 0
    for line in lines[1:]:
        name, _, value = line.partition(":")
        if name.strip().lower() == "content-length":
            length = int(value.strip())
    body = bytearray(rest)
    while len(body) < length:
        chunk = conn.recv(65536)
        if not chunk:
            return None
        body.extend(chunk)
    buffer[:] = body[length:]
    method, target, _ = lines[0].split(" ", 2)
    return f"{method} {target}"


def _serve_connection(conn: socket.socket, owner: StaleConnectionOwner) -> None:
    with conn:
        buffer = bytearray()
        first = _read_request(conn, buffer)
        if first is None:
            return
        owner.received.append(first)
        body = json.dumps({"ok": True, "request": first}).encode()
        # A reply to HEAD has no body (RFC 9110, section 9.3.2).
        payload = b"" if first.startswith("HEAD ") else body
        conn.sendall(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode()
            + payload
        )
        second = _read_request(conn, buffer)
        if second is not None:
            owner.received.append(second)
            owner.dropped.append(second)


@contextmanager
def stale_connection_owner() -> Iterator[StaleConnectionOwner]:
    """Yield an owner that drops the second request on every pooled connection."""
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    listener.settimeout(0.1)
    owner = StaleConnectionOwner(base_url=f"http://127.0.0.1:{listener.getsockname()[1]}")
    stopping = threading.Event()

    def _accept() -> None:
        while not stopping.is_set():
            try:
                conn, _ = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            threading.Thread(target=_serve_connection, args=(conn, owner), daemon=True).start()

    acceptor = threading.Thread(target=_accept, daemon=True)
    acceptor.start()
    try:
        yield owner
    finally:
        stopping.set()
        acceptor.join(timeout=5.0)
        listener.close()
