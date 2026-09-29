"""Blackbox verification test suite for BDD and Playwright governance updates.

Governed by ADR-0010, ADR-0014, and TASK-0360.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_hard_invariant_7_updated_across_governance_records():
    """Verifies Hard Invariant 7 mandates Blackbox TDD & BDD and Playwright browser automation."""
    governance_files = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "docs" / "operating-manual.md",
    ]

    for file_path in governance_files:
        assert file_path.exists(), f"Governance file not found: {file_path}"
        content = file_path.read_text(encoding="utf-8")

        assert "7. **Blackbox TDD & BDD with frontdoor setup.**" in content
        assert "All user flows and UI journeys must be expressed as Gherkin scenarios" in content
        assert "executed through Playwright browser automation" in content
        assert "without private backdoors or database manipulation" in content
        assert "[^26]" in content


def test_definition_of_ready_contains_bdd_requirement():
    """Verifies DoR mandates frontdoor BDD Gherkin scenario readiness across documents."""
    targets = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "docs" / "operating-manual.md",
    ]

    for file_path in targets:
        assert file_path.exists(), f"File not found: {file_path}"
        content = file_path.read_text(encoding="utf-8")

        assert "Frontdoor BDD Scenario Specification" in content
        assert "docs/project/user_stories/accepted/" in content
        assert "Given ... When ... Then" in content
        assert "ADR-0014" in content

    # Backlog README delegates DoR governance directly to AGENTS.md
    readme = REPO_ROOT / "docs" / "project" / "backlog" / "README.md"
    assert readme.exists()
    assert "Definition of Ready in [`AGENTS.md`]" in readme.read_text(encoding="utf-8")


def test_definition_of_ready_mandates_zero_backward_compatibility_shims():
    """Verifies DoR mandates zero backward compatibility shims or re-exports across documents."""
    targets = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "docs" / "operating-manual.md",
        REPO_ROOT / "docs" / "project" / "backlog" / "README.md",
    ]

    for file_path in targets:
        assert file_path.exists(), f"File not found: {file_path}"
        content = file_path.read_text(encoding="utf-8")

        assert "Zero Backward Compatibility Shims" in content
        assert "backward compatibility" in content.lower()
        assert "re-export" in content.lower()


def test_definition_of_done_contains_playwright_e2e_requirement():
    """Verifies DoD mandates passing Playwright BDD browser test suites across documents."""
    targets = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "docs" / "operating-manual.md",
    ]

    for file_path in targets:
        assert file_path.exists(), f"File not found: {file_path}"
        content = file_path.read_text(encoding="utf-8")

        assert "Playwright BDD End-to-End Verification" in content
        assert "headless browser automation" in content
        assert "without backdoor state manipulation" in content
        assert "ADR-0014" in content


def test_playwright_bdd_how_to_guide_exists_and_meets_invariants():
    """Verifies the Diataxis How-To guide for Playwright BDD satisfies repository constraints."""
    guide_path = REPO_ROOT / "docs" / "how-to" / "test-user-flows-with-playwright-bdd.md"
    assert guide_path.exists(), f"How-to guide not found: {guide_path}"

    lines = guide_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 300, f"Guide exceeds 300 lines (actual: {len(lines)})"
    assert len(lines) < 500, "Guide violates Hard Invariant 6 (<500 lines)"

    content = "\n".join(lines)
    # Check required practical recipes
    assert "Authoring Gherkin Features from User Stories" in content
    assert "Managing Frontdoor Test Setup and Authenticated Sessions" in content
    assert "Implementing Step Definitions with Shadow-Piercing Locators" in content
    assert "Running and Debugging Tests Locally" in content
    assert "make test-e2e" in content
    assert "make test-e2e-ui" in content
    assert "make test-bdd" in content


def test_curation_and_decomposition_guides_auditing_guidance():
    """Verifies curation and PRD decomposition guides instruct agents to audit BDD readiness."""
    curate_guide = REPO_ROOT / "docs" / "how-to" / "curate-backlog-and-roadmap.md"
    assert curate_guide.exists()
    curate_content = curate_guide.read_text(encoding="utf-8")
    assert "Auditing BDD Readiness During Curation" in curate_content
    assert "ADR-0014" in curate_content

    decomp_guide = REPO_ROOT / "docs" / "how-to" / "decompose-prds-into-vertical-slices.md"
    assert decomp_guide.exists()
    decomp_content = decomp_guide.read_text(encoding="utf-8")
    assert "Frontdoor Blackbox Verification & BDD Readiness" in decomp_content
    assert "ADR-0014" in decomp_content
