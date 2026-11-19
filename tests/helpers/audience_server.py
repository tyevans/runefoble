"""Test helper to launch, stop, and restart the Audience Studio Fastify server.

The service verifies Zitadel tokens (TASK-0533). The helper serves a test JWKS over local HTTP,
so the service fetches its keys from a real URL. Tests mint tokens with the same issuer.
Permission checks go to a live SpiceDB container (TASK-0554). Tests pass its env through
`env_overrides`, for example `LiveSpiceDB.env`.
"""

import json
import os
import subprocess
import threading
import urllib.parse
from collections.abc import Generator, Mapping
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

from tests.helpers.polling import wait_until
from tests.helpers.ports import free_port
from tests.helpers.signing_test_issuer import (
    DEFAULT_AUDIENCE,
    DEFAULT_ISSUER,
    SigningTestIssuer,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICE_DIR = REPO_ROOT / "services" / "audience_studio"


@lru_cache(maxsize=1)
def shared_issuer() -> SigningTestIssuer:
    """One signing key for the whole test session. Restarted processes trust the same tokens."""
    return SigningTestIssuer()


def bearer_for(sub: str) -> dict[str, str]:
    """Authorization header for a verified token of subject `sub`."""
    return {"Authorization": f"Bearer {shared_issuer().mint(sub)}"}


class _JwksServer:
    """Serves OIDC discovery and one JWK set on 127.0.0.1. Answers only the issuer host."""

    def __init__(self, issuer: SigningTestIssuer) -> None:
        keys = json.dumps(issuer.jwks()).encode("utf-8")
        discovery = json.dumps({"jwks_uri": f"{issuer.issuer}/oauth/v2/keys"}).encode("utf-8")
        issuer_host = urllib.parse.urlsplit(issuer.issuer).netloc
        routes = {
            "/.well-known/openid-configuration": discovery,
            "/oauth/v2/keys": keys,
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server naming
                body = routes.get(self.path)
                if self.headers.get("Host") != issuer_host or body is None:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def build_audience_studio() -> None:
    """Compile the TypeScript service so the tests run the current code. A build failure fails the test."""
    subprocess.run(
        ["pnpm", "--filter", "@runefoble/audience-studio", "run", "build"],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        timeout=240.0,
    )


class AudienceStudioProcess:
    """One Audience Studio process. Start and stop it as often as a test needs."""

    def __init__(
        self, env_overrides: Mapping[str, str] | None = None, port: int | None = None
    ) -> None:
        self.port = port or free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._env_overrides = dict(env_overrides or {})
        self._proc: subprocess.Popen[bytes] | None = None
        self.issuer = shared_issuer()
        self._jwks: _JwksServer | None = None

    def token(self, sub: str) -> str:
        """Mint a token that the running service accepts for subject `sub`."""
        return self.issuer.mint(sub)

    def start(self, wait_healthy: bool = True) -> str:
        """Start the process. Wait for /healthz when asked. Raise with the logs if it exits early."""
        env = os.environ.copy()
        # A developer shell may hold a database URL. Each test opts in explicitly.
        env.pop("RUNEFOBLE_DATABASE_URL", None)
        env.pop("RUNEFOBLE_SPICEDB_ENDPOINT", None)
        env.pop("RUNEFOBLE_SPICEDB_PRESHARED_KEY", None)
        env.update(
            {
                "PORT": str(self.port),
                "HOST": "127.0.0.1",
                "NODE_ENV": "test",
                "RUNEFOBLE_REDIS_URL": "mock://redis",
                "RUNEFOBLE_ZITADEL_ISSUER": DEFAULT_ISSUER,
                "RUNEFOBLE_ZITADEL_AUDIENCE": DEFAULT_AUDIENCE,
            }
        )
        env.update(self._env_overrides)

        # A fresh JWKS server per start. The key pair is kept, so tokens stay valid across restarts.
        self._jwks = _JwksServer(self.issuer)
        env["RUNEFOBLE_ZITADEL_INTERNAL_URL"] = self._jwks.url

        dist_index = SERVICE_DIR / "dist" / "index.js"
        build_audience_studio()
        self._proc = subprocess.Popen(
            ["node", str(dist_index)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if wait_healthy:
            self.wait_for_status("/healthz", 200, timeout=10.0)
        return self.base_url

    def wait_for_status(self, path: str, status: int, timeout: float) -> None:
        """Poll a path until it returns the status, or raise with the process logs."""
        with httpx.Client(base_url=self.base_url) as client:

            def returns_status() -> bool:
                if self._proc is not None and self._proc.poll() is not None:
                    raise RuntimeError(f"Audience Studio exited early:\n{self._logs()}")
                try:
                    return client.get(path, timeout=1.0).status_code == status
                except httpx.HTTPError:
                    return False

            if wait_until(returns_status, timeout_s=timeout, interval_s=0.1):
                return
        raise RuntimeError(f"{path} did not return {status} within {timeout}s:\n{self._logs()}")

    def _logs(self) -> str:
        if self._proc is None:
            return ""
        self._proc.terminate()
        try:
            stdout, stderr = self._proc.communicate(timeout=3.0)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            stdout, stderr = self._proc.communicate()
        return f"STDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"

    def stop(self) -> None:
        """Stop the process and its JWKS server. Stopping is graceful, so the server can close its timers."""
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
            self._proc = None
        if self._jwks is not None:
            self._jwks.stop()
            self._jwks = None


def start_audience_studio_server(
    env_overrides: Mapping[str, str] | None = None,
) -> Generator[AudienceStudioProcess]:
    """Start Audience Studio Fastify server as subprocess and yield it for the test module."""
    process = AudienceStudioProcess(env_overrides)
    process.start()
    try:
        yield process
    finally:
        process.stop()
