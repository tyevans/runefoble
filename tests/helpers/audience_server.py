"""Test helper to launch, stop, and restart the Audience Studio Fastify server."""

import os
import socket
import subprocess
import time
from collections.abc import Generator, Mapping
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICE_DIR = REPO_ROOT / "services" / "audience_studio"


def get_free_port() -> int:
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def build_audience_studio() -> None:
    """Compile the TypeScript service so the tests run the current code. A build failure fails the test."""
    subprocess.run(
        ["pnpm", "--filter", "@runefoble/audience-studio", "run", "build"],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
    )


class AudienceStudioProcess:
    """One Audience Studio process. Start and stop it as often as a test needs."""

    def __init__(
        self, env_overrides: Mapping[str, str] | None = None, port: int | None = None
    ) -> None:
        self.port = port or get_free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._env_overrides = dict(env_overrides or {})
        self._proc: subprocess.Popen[bytes] | None = None

    def start(self, wait_healthy: bool = True) -> str:
        """Start the process. Wait for /healthz when asked. Raise with the logs if it exits early."""
        env = os.environ.copy()
        # A developer shell may hold a database URL. Each test opts in explicitly.
        env.pop("RUNEFOBLE_DATABASE_URL", None)
        env.update(
            {
                "PORT": str(self.port),
                "HOST": "127.0.0.1",
                "NODE_ENV": "test",
                "REDIS_URL": "mock://redis",
            }
        )
        env.update(self._env_overrides)

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
        deadline = time.time() + timeout
        with httpx.Client(base_url=self.base_url) as client:
            while time.time() < deadline:
                if self._proc is not None and self._proc.poll() is not None:
                    raise RuntimeError(f"Audience Studio exited early:\n{self._logs()}")
                try:
                    if client.get(path, timeout=1.0).status_code == status:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
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
        """Stop the process. Stopping is graceful, so the server can close its timers."""
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        self._proc = None


def start_audience_studio_server() -> Generator[str]:
    """Start Audience Studio Fastify server as subprocess and yield base URL."""
    process = AudienceStudioProcess()
    base_url = process.start()
    try:
        yield base_url
    finally:
        process.stop()
