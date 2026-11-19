"""Blackbox checks for the gateway import boundary (ADR-0015 b, TASK-0598).

The contract lives in the root pyproject.toml. Each test runs import-linter in a child process,
so the analysis reads the files on disk and nothing else. The negative test builds a small
project in a temporary directory. That project has the same contract, and it adds one forbidden
import to the gateway package.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
GATEWAY_CONTRACT_NAME = "gateway_api must not import a service package (ADR-0015 b, TASK-0775)"
LINT_SCRIPT = (
    "import sys\n"
    "from importlinter.configuration import configure\n"
    "from importlinter.application.use_cases import lint_imports\n"
    "configure()\n"
    "sys.exit(0 if lint_imports(config_filename='pyproject.toml') else 1)\n"
)


def _gateway_contract() -> dict[str, object]:
    """Return the gateway contract as the root pyproject.toml declares it."""
    config = tomllib.loads(ROOT_PYPROJECT.read_text(encoding="utf-8"))
    contracts = config["tool"]["importlinter"]["contracts"]
    matches = [contract for contract in contracts if contract["name"] == GATEWAY_CONTRACT_NAME]
    assert len(matches) == 1, "the root pyproject.toml must declare the gateway contract once"
    return matches[0]


def _run_lint(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", LINT_SCRIPT],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _write_project(project: Path, gateway_main: str) -> None:
    """Write a project with the gateway contract, a gateway package, and each forbidden package.

    Each forbidden package exists as an empty package, so import-linter treats it as internal.
    """
    contract = _gateway_contract()
    forbidden = [str(name) for name in contract["forbidden_modules"]]  # type: ignore[union-attr]
    roots = json.dumps(["gateway_api", *forbidden])
    project.joinpath("pyproject.toml").write_text(
        "[tool.importlinter]\n"
        f"root_packages = {roots}\n\n"
        "[[tool.importlinter.contracts]]\n"
        f'name = "{GATEWAY_CONTRACT_NAME}"\n'
        'type = "forbidden"\n'
        'source_modules = ["gateway_api"]\n'
        f"forbidden_modules = {json.dumps(forbidden)}\n",
        encoding="utf-8",
    )
    gateway = project / "gateway_api"
    gateway.mkdir()
    gateway.joinpath("__init__.py").write_text("", encoding="utf-8")
    gateway.joinpath("main.py").write_text(gateway_main, encoding="utf-8")
    for name in forbidden:
        package = project / name
        package.mkdir()
        package.joinpath("__init__.py").write_text("", encoding="utf-8")


def test_gateway_api_imports_no_service_package() -> None:
    result = _run_lint(REPO_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert GATEWAY_CONTRACT_NAME in result.stdout
    assert "KEPT" in result.stdout


def test_gateway_contract_passes_when_gateway_imports_only_its_own_package(tmp_path: Path) -> None:
    _write_project(tmp_path, gateway_main="import json\n")

    result = _run_lint(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_gateway_contract_fails_when_gateway_imports_a_service_package(tmp_path: Path) -> None:
    _write_project(tmp_path, gateway_main="import board_state\n")

    result = _run_lint(tmp_path)

    assert result.returncode != 0
    assert GATEWAY_CONTRACT_NAME in result.stdout
    assert "BROKEN" in result.stdout
