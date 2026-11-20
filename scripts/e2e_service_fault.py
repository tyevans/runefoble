"""Stop or start one Kind service for the e2e fault journeys (TASK-0909).

Usage: e2e_service_fault.py <service> down|up

`down` scales the service deployment in the `kind-runefoble-local` context to 0 replicas.
Then it waits until the gateway `/healthz` report shows the service as `unreachable`.
`up` scales the deployment to 1 replica and waits for the rollout. Then it waits until the
gateway report shows the service as `operational`.

The script controls only the deployments in `DEPLOYMENTS`. It changes no data. It reads the
gateway URL from `PLAYWRIGHT_BASE_URL` (default `http://localhost`, the Kind ingress), and the
wait limit in seconds from `RUNEFOBLE_E2E_FAULT_TIMEOUT_S` (default 180).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

KUBE_CONTEXT = "kind-runefoble-local"
# Gateway health key -> Kind deployment name. No other deployment can be scaled.
DEPLOYMENTS = {
    "campaign_lore": "campaign-lore",
    "game_session": "game-session",
    "the_watcher": "the-watcher",
}
TARGET = {"down": (0, "unreachable"), "up": (1, "operational")}
POLL_INTERVAL_S = 0.5


class FaultError(Exception):
    """A step failed. The message says which step and why."""


def _timeout_s() -> float:
    return float(os.environ.get("RUNEFOBLE_E2E_FAULT_TIMEOUT_S", "180"))


def _kubectl(*args: str) -> None:
    command = ["kubectl", "--context", KUBE_CONTEXT, *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise FaultError(f"{' '.join(command)} failed: {result.stderr.strip()}")


def _reported_status(base_url: str, service: str) -> str:
    """Return the gateway report for the service. A gateway that cannot answer gives ''."""
    try:
        with urllib.request.urlopen(f"{base_url}/healthz", timeout=5) as reply:
            report = json.load(reply)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return ""
    services = report.get("downstream_services", {})
    if service not in services:
        raise FaultError(
            f"The gateway /healthz does not report {service}. Deploy a gateway image that probes it."
        )
    return services[service]


def _wait_for_status(base_url: str, service: str, wanted: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    status = _reported_status(base_url, service)
    while status != wanted:
        if time.monotonic() >= deadline:
            raise FaultError(
                f"The gateway reports {service} as '{status}' after {timeout_s:g} s. "
                f"Expected '{wanted}'."
            )
        time.sleep(POLL_INTERVAL_S)
        status = _reported_status(base_url, service)


def run(service: str, action: str) -> None:
    deployment = f"deployment/{DEPLOYMENTS[service]}"
    replicas, wanted = TARGET[action]
    timeout_s = _timeout_s()
    base_url = os.environ.get("PLAYWRIGHT_BASE_URL", "http://localhost").rstrip("/")
    _kubectl("scale", deployment, f"--replicas={replicas}")
    if action == "up":
        _kubectl("rollout", "status", deployment, f"--timeout={timeout_s:g}s")
    _wait_for_status(base_url, service, wanted, timeout_s)
    print(f"The gateway reports {service} as {wanted}.")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in DEPLOYMENTS or argv[1] not in TARGET:
        services = "|".join(DEPLOYMENTS)
        print(f"Usage: e2e_service_fault.py {services} down|up", file=sys.stderr)
        return 2
    try:
        run(argv[0], argv[1])
    except FaultError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
