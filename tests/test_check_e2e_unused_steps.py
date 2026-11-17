"""Behaviour tests for the e2e unused-step check (scripts/check_e2e_unused_steps.py).

Governed by ADR-0014. The tests run the CLI against temporary step and feature trees.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_e2e_unused_steps.py"


def _run(steps: str, features: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    steps_dir = tmp_path / "steps"
    features_dir = tmp_path / "features"
    steps_dir.mkdir()
    features_dir.mkdir()
    (steps_dir / "steps.ts").write_text(steps, encoding="utf-8")
    (features_dir / "flow.feature").write_text(features, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--steps-dir",
            str(steps_dir),
            "--features-dir",
            str(features_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_fails_and_names_a_definition_that_no_feature_uses(tmp_path):
    steps = (
        "Given('I am logged in as a {string}', async () => {});\n"
        "Then('I should see a toast notification containing {string}', async () => {});\n"
    )
    features = 'Feature: Login\n  Scenario: Logs in\n    Given I am logged in as a "DM"\n'

    result = _run(steps, features, tmp_path)

    assert result.returncode == 1
    assert 'unused step definition "I should see a toast notification containing {string}"' in (
        result.stdout
    )
    assert "I am logged in" not in result.stdout


def test_passes_when_every_definition_is_used(tmp_path):
    steps = (
        "When(\n  '{word} clicks {string}',\n  async () => {},\n);\n"
        "Then(/^the count is (\\d+)$/, async () => {});\n"
    )
    features = (
        "Feature: Mixed\n"
        "  Scenario: Uses every definition\n"
        '    When Marcus clicks "Save"\n'
        "    Then the count is 3\n"
    )

    result = _run(steps, features, tmp_path)

    assert result.returncode == 0, result.stderr
    assert "all 2 step definitions are used" in result.stdout


def test_literal_angle_bracket_text_matches_and_outline_placeholder_matches(tmp_path):
    steps = (
        "Then('the card renders <runefoble-board>', async () => {});\n"
        "When('Evelyn enters {string} items', async () => {});\n"
    )
    features = (
        "Feature: Literal and outline\n"
        "  Scenario Outline: Counts\n"
        '    When Evelyn enters "<count>" items\n'
        "    Then the card renders <runefoble-board>\n"
    )

    result = _run(steps, features, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_fails_loudly_on_a_definition_it_cannot_read(tmp_path):
    steps = "When(someExpression, async () => {});\n"
    features = "Feature: Unreadable\n  Scenario: Reads\n    When anything happens\n"

    result = _run(steps, features, tmp_path)

    assert result.returncode == 2
    assert "must be a string or regex literal" in result.stderr


def test_fails_when_no_definitions_are_found(tmp_path):
    result = _run("export const nothing = 1;\n", "Feature: Empty\n", tmp_path)

    assert result.returncode == 2
    assert "no step definitions found" in result.stderr
