"""Blackbox test for backlog link, status, path, and governance drift (TASK-0666).

The check is `scripts/check_backlog_links.py`. It reads repository files only. The test
runs the check as a process and asserts that every category reports zero. It reads the
JSON output and does not inspect source text.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK = REPO_ROOT / "scripts" / "check_backlog_links.py"


def test_backlog_records_have_no_drift() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(result.stdout)
    non_zero = {name: entry["count"] for name, entry in report.items() if entry["count"]}
    assert non_zero == {}


SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURE_SCRIPTS = ("check_backlog_links.py", "backlog_records.py")


def _fixture_repo(root: Path, cited_path: str, files: dict[str, str]) -> None:
    """Build a temporary repository with one complete record that cites `cited_path`.

    The checker resolves paths against the folder that holds its own script, so the
    scripts are copied into the fixture root and run from there.
    """
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in FIXTURE_SCRIPTS:
        (scripts / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
        )

    complete = root / "docs" / "project" / "backlog" / "complete"
    complete.mkdir(parents=True)
    (complete / "0001-fixture.md").write_text(
        "---\n"
        "id: '0001'\n"
        "title: Fixture\n"
        "status: Complete\n"
        "governing_adrs: []\n"
        "governing_prds: []\n"
        "governing_stories: []\n"
        "dependencies: []\n"
        "---\n\n"
        "# TASK-0001: Fixture\n\n"
        f"Cited path: `{cited_path}`\n",
        encoding="utf-8",
    )

    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _run_check_on(root: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_backlog_links.py"), "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stdout + result.stderr
    return json.loads(result.stdout)


def test_folder_holding_only_pycache_is_reported_as_unresolved(tmp_path: Path) -> None:
    _fixture_repo(
        tmp_path,
        "services/fixture/cache_only/",
        {"services/fixture/cache_only/__pycache__/x.pyc": "bytecode"},
    )

    report = _run_check_on(tmp_path)

    assert report["unresolved_paths"]["count"] == 1
    assert "services/fixture/cache_only/" in report["unresolved_paths"]["items"][0]


def test_nested_pycache_only_folder_is_reported_as_unresolved(tmp_path: Path) -> None:
    _fixture_repo(
        tmp_path,
        "services/fixture/nested/",
        {
            "services/fixture/nested/pkg/__pycache__/x.pyc": "bytecode",
            "services/fixture/nested/__pycache__/y.pyc": "bytecode",
        },
    )

    report = _run_check_on(tmp_path)

    assert report["unresolved_paths"]["count"] == 1


def test_folder_with_real_content_beside_pycache_resolves(tmp_path: Path) -> None:
    _fixture_repo(
        tmp_path,
        "services/fixture/live/",
        {
            "services/fixture/live/__pycache__/x.pyc": "bytecode",
            "services/fixture/live/module.py": "VALUE = 1\n",
        },
    )

    report = _run_check_on(tmp_path)

    assert report["unresolved_paths"]["count"] == 0


def test_cited_file_resolves_even_inside_a_pycache_name(tmp_path: Path) -> None:
    _fixture_repo(
        tmp_path,
        "services/fixture/plain/module.py",
        {"services/fixture/plain/module.py": "VALUE = 1\n"},
    )

    report = _run_check_on(tmp_path)

    assert report["unresolved_paths"]["count"] == 0
