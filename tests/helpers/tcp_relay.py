"""A loopback TCP relay that stands for a dependency that is not up yet (TASK-0929).

The relay binds a port at once but does not listen. A client that connects gets
"connection refused", as when a dependency pod has not started. `come_up()` starts to
listen and forwards each connection to the real dependency. The client keeps the same
address, so the test changes only the network, never the code under test.
"""

from __future__ import annotations

import socket
import threading
from types import TracebackType


class TcpRelay:
    """Forward 127.0.0.1:<port> to a target host and port after `come_up()`."""

    def __init__(self, target_host: str, target_port: int) -> None:
        self._target = (target_host, target_port)
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._stopped = threading.Event()
        self._sockets: list[socket.socket] = []
        self._threads: list[threading.Thread] = []

    @property
    def port(self) -> int:
        return int(self._listener.getsockname()[1])

    def come_up(self) -> None:
        """Start to accept connections and forward them to the target."""
        self._listener.listen(64)
        self._listener.settimeout(0.2)
        self._start(self._accept_loop)

    def close(self) -> None:
        """Stop the relay and close every socket that it opened."""
        self._stopped.set()
        for sock in [self._listener, *self._sockets]:
            try:
                sock.close()
            except OSError:
                continue
        for thread in self._threads:
            thread.join(timeout=2)

    def __enter__(self) -> TcpRelay:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _start(self, target: object, *args: object) -> None:
        thread = threading.Thread(target=target, args=args, daemon=True)  # type: ignore[arg-type]
        self._threads.append(thread)
        thread.start()

    def _accept_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                client, _ = self._listener.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            upstream = socket.create_connection(self._target, timeout=5)
            upstream.settimeout(None)
            client.settimeout(None)
            self._sockets.extend([client, upstream])
            self._start(self._pump, client, upstream)
            self._start(self._pump, upstream, client)

    def _pump(self, source: socket.socket, sink: socket.socket) -> None:
        try:
            while chunk := source.recv(65536):
                sink.sendall(chunk)
        except OSError:
            return  # The peer closed the connection. The finally block closes both ends.
        finally:
            for sock in (source, sink):
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    continue


__all__ = ["TcpRelay"]
