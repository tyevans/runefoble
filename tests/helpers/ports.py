"""Find free local TCP ports for test servers."""

from __future__ import annotations

import socket


def free_port() -> int:
    """Return a local TCP port that the OS reports as free at the time of the call.

    The port is free only until another process binds it, so callers should bind it promptly.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])
