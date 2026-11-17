"""Fail when a service that owns AggregateRepository state lacks the PostgreSQL event store.

Owners are found in source: a service owns state when its non-test code calls
create_aggregate_repository or constructs AggregateRepository. Each owner must
render as a Kubernetes Deployment with RUNEFOBLE_USE_POSTGRES_EVENT_STORE set
to "true" and a RUNEFOBLE_DATABASE_URL.

Usage: python3 scripts/check_helm_event_store.py [CHART_DIR]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES_DIR = REPO_ROOT / "services"
DEFAULT_CHART = REPO_ROOT / "deployments" / "helm" / "runefoble"
OWNER_PATTERN = re.compile(r"create_aggregate_repository\(|AggregateRepository\(")


def discover_owners() -> list[str]:
    """Return deployment names for services whose source creates aggregate repositories."""
    owners: list[str] = []
    for service_dir in sorted(SERVICES_DIR.iterdir()):
        src = service_dir / "src"
        if not src.is_dir():
            continue
        for path in src.rglob("*.py"):
            if "tests" in path.parts:
                continue
            if OWNER_PATTERN.search(path.read_text(encoding="utf-8")):
                owners.append(service_dir.name.replace("_", "-"))
                break
    return owners


def render_deployments(chart_dir: Path) -> dict[str, dict[str, str]]:
    """Render the chart and map each Deployment name to its container env."""
    result = subprocess.run(
        ["helm", "template", "runefoble", str(chart_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    deployments: dict[str, dict[str, str]] = {}
    for doc in yaml.safe_load_all(result.stdout):
        if not doc or doc.get("kind") != "Deployment":
            continue
        container = doc["spec"]["template"]["spec"]["containers"][0]
        env = {e["name"]: str(e.get("value", "")) for e in container.get("env", [])}
        deployments[doc["metadata"]["name"]] = env
    return deployments


def main(argv: list[str]) -> int:
    chart_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_CHART
    owners = discover_owners()
    deployments = render_deployments(chart_dir)

    failures: list[str] = []
    for name in owners:
        if name not in deployments:
            failures.append(f"{name}: owns aggregate state but has no Deployment in the chart")
            continue
        env = deployments[name]
        if env.get("RUNEFOBLE_USE_POSTGRES_EVENT_STORE") != "true":
            failures.append(f'{name}: RUNEFOBLE_USE_POSTGRES_EVENT_STORE is not "true"')
        if not env.get("RUNEFOBLE_DATABASE_URL"):
            failures.append(f"{name}: RUNEFOBLE_DATABASE_URL is missing")

    if failures:
        print("Event store Helm check failed:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print(f"Event store Helm check passed for {len(owners)} aggregate-owning services.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
