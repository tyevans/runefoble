"""Blackbox tests for the Helm event-store gate (scripts/check_helm_event_store.py).

Governed by:
- ADR-0015 decision (f): every deployed aggregate owner uses the PostgreSQL event store
- TASK-0709: the gate covers the TypeScript Audience Studio owner
- Hard Invariant 7: Blackbox TDD with frontdoor setup

The gate runs as a process on a copy of the chart. Only the chart values are changed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.check_helm_event_store import discover_owners
from tests.helpers.helm import require_helm

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = REPO_ROOT / "deployments" / "helm" / "runefoble"
GATE = REPO_ROOT / "scripts" / "check_helm_event_store.py"


def _run_gate(chart_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), str(chart_dir)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.fixture
def helm_required() -> None:
    require_helm()


def test_gate_passes_on_the_chart(helm_required: None) -> None:
    result = _run_gate(CHART_DIR)

    assert result.returncode == 0, result.stdout + result.stderr


def test_gate_fails_when_audience_studio_has_no_event_store(
    tmp_path: Path, helm_required: None
) -> None:
    chart = tmp_path / "runefoble"
    shutil.copytree(CHART_DIR, chart)
    values_path = chart / "values.yaml"
    values = yaml.safe_load(values_path.read_text(encoding="utf-8"))
    values["services"]["audienceStudio"]["eventStore"] = False
    values_path.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")

    result = _run_gate(chart)

    assert result.returncode != 0
    assert "audience-studio" in result.stdout
    assert "RUNEFOBLE_EVENT_STORE_BACKEND" in result.stdout


def test_discover_owners_reads_typescript_and_python_source_only(tmp_path: Path) -> None:
    services = tmp_path / "services"
    _write(
        services / "ts_owner" / "src" / "server.ts",
        "const repo = new AudienceEventRepository(store, relay);\n",
    )
    _write(
        services / "py_owner" / "src" / "app" / "main.py",
        "repo = create_aggregate_repository(settings)\n",
    )
    _write(
        services / "ts_in_tests" / "src" / "test" / "fixture.ts",
        "new AudienceEventRepository(s, r);\n",
    )
    _write(
        services / "ts_in_test_file" / "src" / "server.test.ts",
        "new AudienceEventRepository(s, r);\n",
    )
    _write(services / "ts_in_python" / "src" / "server.py", "new AudienceEventRepository(s, r)\n")
    _write(services / "no_owner" / "src" / "readme.ts", "export const value = 1;\n")

    assert discover_owners(services) == ["py-owner", "ts-owner"]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
