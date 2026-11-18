"""Blackbox checks that the event and CLI reference pages match the code.

The tests read only repository files. They run the catalogue generator as a
subprocess and do not use the network.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "scripts" / "generate_event_catalogue.py"
CATALOGUE = REPO_ROOT / "docs" / "reference" / "event-identifiers.md"
REFERENCE_DIR = REPO_ROOT / "docs" / "reference"
CLI_REFERENCE = REFERENCE_DIR / "cli-interfaces.md"
MAKEFILE = REPO_ROOT / "Makefile"

BACKTICKED = re.compile(r"`([^`\s]+)`")
DOTTED_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*(?:\.[a-z0-9_]+)+")
CATALOGUE_ROW = re.compile(r"^\| `([^`]+)` \| `[^`]+` \| `[^`]+` \|$", re.MULTILINE)
MAKE_TARGET_ROW = re.compile(r"^\| `make ([a-z][a-z0-9-]*)[` ]", re.MULTILINE)
MAKE_TARGET_DEF = re.compile(r"^([a-zA-Z][a-zA-Z0-9_-]*):", re.MULTILINE)


def _event_reference_pages() -> list[Path]:
    pages = [REFERENCE_DIR / "events-schema.md"]
    pages.extend(sorted(REFERENCE_DIR.glob("events-catalog-*.md")))
    return pages


def _cited_event_identifiers() -> set[str]:
    cited: set[str] = set()
    for page in _event_reference_pages():
        for token in BACKTICKED.findall(page.read_text(encoding="utf-8")):
            if not DOTTED_IDENTIFIER.fullmatch(token):
                continue
            if token.endswith(".py") or token.startswith(("runefoble_events.", "eventsource.")):
                continue
            # Stream names such as runefoble.events.session are not event identifiers.
            if re.fullmatch(r"runefoble\.events\.[a-z_]+", token):
                continue
            cited.add(token)
    return cited


def _generated_identifiers() -> set[str]:
    return set(CATALOGUE_ROW.findall(CATALOGUE.read_text(encoding="utf-8")))


def _makefile_targets() -> set[str]:
    return set(MAKE_TARGET_DEF.findall(MAKEFILE.read_text(encoding="utf-8")))


def test_generated_catalogue_is_current_with_registry():
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_every_cited_event_identifier_is_in_generated_catalogue():
    cited = _cited_event_identifiers()
    generated = _generated_identifiers()
    assert cited, "no event identifiers found in the event reference pages"
    unknown = sorted(cited - generated)
    assert not unknown, f"event identifiers cited but not emitted by code: {unknown}"


def test_every_make_target_in_cli_reference_exists_in_makefile():
    documented = set(MAKE_TARGET_ROW.findall(CLI_REFERENCE.read_text(encoding="utf-8")))
    assert documented, "no make targets found in cli-interfaces.md"
    missing = sorted(documented - _makefile_targets())
    assert not missing, f"make targets documented but absent from Makefile: {missing}"


def test_every_makefile_target_is_listed_in_cli_reference():
    documented = set(MAKE_TARGET_ROW.findall(CLI_REFERENCE.read_text(encoding="utf-8")))
    # Variables and the implicit `.PHONY` line are not targets.
    undocumented = sorted(_makefile_targets() - documented - {"PHONY"})
    assert not undocumented, f"Makefile targets missing from cli-interfaces.md: {undocumented}"
