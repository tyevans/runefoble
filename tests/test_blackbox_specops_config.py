"""Blackbox checks for the spec-ops configuration and ADR registry (TASK-0664).

Governed by Hard Invariant 7. The tests read the public configuration file
(`specops.toml`) and the public ADR registry (`docs/project/adrs/REGISTRY.md`).
They assert observable contract values only.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SPECOPS_TOML = REPO_ROOT / "specops.toml"
ADR_DIR = REPO_ROOT / "docs" / "project" / "adrs" / "accepted"
ADR_REGISTRY = REPO_ROOT / "docs" / "project" / "adrs" / "REGISTRY.md"


@pytest.fixture(scope="module")
def specops_config() -> dict:
    assert SPECOPS_TOML.is_file(), "specops.toml must exist at the repository root"
    with SPECOPS_TOML.open("rb") as handle:
        return tomllib.load(handle)


def test_project_identity_is_runefoble(specops_config: dict) -> None:
    assert specops_config["project"]["name"] == "Runefoble"
    assert specops_config["project"]["docs_dir"] == "docs/project"


def test_architecture_limits_match_hard_invariants(specops_config: dict) -> None:
    architecture = specops_config["architecture"]
    assert architecture["file_length_limit"] == 500
    assert architecture["buffer_target"] == 10
    assert architecture["buffer_warning_threshold"] == 6


def test_components_cover_every_platform_root(specops_config: dict) -> None:
    paths = {component["path"] for component in specops_config["architecture"]["components"]}
    assert {"libs", "services", "gateway/api", "gateway/mcp", "frontend"} <= paths


def test_quality_requires_blackbox_frontdoor_and_bdd(specops_config: dict) -> None:
    quality = specops_config["quality"]
    assert quality["testing_style"] == "blackbox-frontdoor"
    assert quality["require_bdd"] is True
    assert quality["preflight"] == ["uv run pytest"]


def test_execution_isolates_backlog_in_worktrees(specops_config: dict) -> None:
    execution = specops_config["execution"]
    assert execution["backlog_isolation"] is True
    assert execution["git_branch_prefix"] == "task/"


def _registry_adr_ids() -> set[str]:
    text = ADR_REGISTRY.read_text(encoding="utf-8")
    return set(re.findall(r"^\| (ADR-\d{4}) \|", text, flags=re.MULTILINE))


def test_every_accepted_adr_file_has_a_registry_row() -> None:
    adr_files = sorted(ADR_DIR.glob("adr-*.md"))
    assert adr_files, "accepted ADR directory must not be empty"
    registry_text = ADR_REGISTRY.read_text(encoding="utf-8")
    registry_ids = _registry_adr_ids()
    missing = []
    for adr_file in adr_files:
        number = re.match(r"adr-(\d{4})-", adr_file.name)
        assert number is not None, f"unexpected ADR file name: {adr_file.name}"
        adr_id = f"ADR-{number.group(1)}"
        if adr_id not in registry_ids or adr_file.name not in registry_text:
            missing.append(adr_id)
    assert missing == [], f"ADR files without a REGISTRY.md row: {missing}"


def test_spec_ops_baseline_adrs_are_mapped_in_registry() -> None:
    text = ADR_REGISTRY.read_text(encoding="utf-8")
    assert "spec-ops baseline" in text.lower()
    for topic in ("Spec as code", "File length", "Worktree", "Agent constitution"):
        assert topic in text, f"ADR mapping must cover: {topic}"


def test_security_profile_decision_is_recorded_with_date() -> None:
    text = ADR_REGISTRY.read_text(encoding="utf-8")
    assert re.search(r"spec-ops security profile.*\d{4}-\d{2}-\d{2}", text, flags=re.IGNORECASE)
