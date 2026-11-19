"""Blackbox test: production modules do not load the SpiceDB mock client (TASK-0911, TASK-0912).

A fresh interpreter imports a production module. The test double package
`runefoble_auth.mock` must stay out of `sys.modules`.
"""

import subprocess
import sys

import pytest

PROBE = """
import importlib
import sys
for name in sys.argv[1:]:
    importlib.import_module(name)
loaded = sorted(name for name in sys.modules if name.startswith("runefoble_auth.mock"))
print(",".join(loaded))
"""


def _mock_modules_loaded_by(*modules: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", PROBE, *modules],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return result.stdout.strip()


def test_production_spicedb_modules_do_not_load_the_mock() -> None:
    assert (
        _mock_modules_loaded_by(
            "runefoble_auth.factory", "runefoble_auth.spicedb", "runefoble_auth.sync"
        )
        == ""
    )


@pytest.mark.parametrize(
    "service_main",
    [
        "character_sheet.main",
        "game_session.main",
        "rules_compendium.main",
        "asset_forge.main",
        "campaign_analytics.main",
        "campaign_lore.main",
        "soundscape.main",
    ],
)
def test_service_main_does_not_load_the_mock(service_main: str) -> None:
    assert _mock_modules_loaded_by(service_main) == ""
