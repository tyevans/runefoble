"""Behaviour tests for the hex colour gate (scripts/check_hex_literals.py).

Governed by ADR-0012 and ADR-0004 (TASK-0763). The tests run the public CLI against a
temporary repository tree and a temporary baseline file.
"""

import json
import subprocess
import sys
from pathlib import Path

from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_hex_literals.py"

COMPONENT = "services/demo/ui/src/runefoble-demo.styles.ts"
THEME = "frontend/src/styles/themes/demo.css"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(
    root: Path, baseline: dict[str, int] | None, *extra: str
) -> subprocess.CompletedProcess[str]:
    baseline_path = root / "hex_baseline.json"
    if baseline is not None:
        baseline_path.write_text(json.dumps({"files": baseline}), encoding="utf-8")
    return run_command(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--baseline",
            str(baseline_path),
            *extra,
        ],
        check=False,
        timeout=60.0,
    )


def _baseline_files(root: Path) -> dict[str, int]:
    return json.loads((root / "hex_baseline.json").read_text(encoding="utf-8"))["files"]


def test_fails_and_names_a_new_hex_literal_in_a_component(tmp_path):
    _write(tmp_path, COMPONENT, "css`\n  :host { color: #e63946; }\n`;\n")

    result = _run(tmp_path, {})

    assert result.returncode == 1
    assert f"{COMPONENT}:2" in result.stdout
    assert "#e63946" in result.stdout


def test_counts_a_hex_fallback_inside_var_as_a_literal(tmp_path):
    _write(tmp_path, COMPONENT, "css`:host { color: var(--rf-text-primary, #121212); }`;\n")

    result = _run(tmp_path, {})

    assert result.returncode == 1
    assert "#121212" in result.stdout


def test_passes_when_components_use_only_tokens(tmp_path):
    _write(tmp_path, COMPONENT, "css`:host { color: var(--rf-text-primary); }`;\n")

    result = _run(tmp_path, {})

    assert result.returncode == 0, result.stdout + result.stderr


def test_passes_for_hex_literals_in_token_definition_files(tmp_path):
    _write(tmp_path, THEME, ":root { --rf-color-red: #e63946; }\n")

    result = _run(tmp_path, {})

    assert result.returncode == 0, result.stdout + result.stderr


def test_passes_when_count_is_at_or_below_the_baseline(tmp_path):
    _write(tmp_path, COMPONENT, "css`a { color: #fff; } b { color: #000000; }`;\n")

    assert _run(tmp_path, {COMPONENT: 2}).returncode == 0
    assert _run(tmp_path, {COMPONENT: 5}).returncode == 0


def test_fails_when_count_exceeds_the_baseline_for_a_file(tmp_path):
    _write(tmp_path, COMPONENT, "css`a { color: #fff; } b { color: #000000; }`;\n")

    result = _run(tmp_path, {COMPONENT: 1})

    assert result.returncode == 1
    assert COMPONENT in result.stdout
    assert "2" in result.stdout


def test_ignores_text_that_is_not_a_hex_colour(tmp_path):
    source = (
        "class A { #cafe = 1; run() { return this.#bad; } }\n"
        "const id = '#add-button';\n"
        "const entity = '&#x27;';\n"
        "const issue = 'see #1234567';\n"
    )
    _write(tmp_path, COMPONENT, source)

    result = _run(tmp_path, {})

    assert result.returncode == 0, result.stdout + result.stderr


def test_update_baseline_lowers_counts_and_drops_clean_files(tmp_path):
    _write(tmp_path, COMPONENT, "css`a { color: #fff; }`;\n")
    clean = "services/demo/ui/src/clean.ts"
    _write(tmp_path, clean, "export const x = 1;\n")

    result = _run(tmp_path, {COMPONENT: 3, clean: 2}, "--update-baseline")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _baseline_files(tmp_path) == {COMPONENT: 1}


def test_update_baseline_refuses_to_raise_a_count(tmp_path):
    _write(tmp_path, COMPONENT, "css`a { color: #fff; } b { color: #000; }`;\n")

    result = _run(tmp_path, {COMPONENT: 1}, "--update-baseline")

    assert result.returncode == 1
    assert _baseline_files(tmp_path) == {COMPONENT: 1}


def test_reports_a_missing_baseline_file_as_a_usage_error(tmp_path):
    _write(tmp_path, COMPONENT, "css`a { color: var(--rf-text-primary); }`;\n")

    result = _run(tmp_path, None)

    assert result.returncode == 2
    assert "baseline" in result.stderr.lower()
