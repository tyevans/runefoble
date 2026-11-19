"""Blackbox test: the production SpiceDB modules do not load the mock client (TASK-0911).

A fresh interpreter imports the public production modules of `runefoble_auth`. The test double
package `runefoble_auth.mock` must stay out of `sys.modules`.
"""

import subprocess
import sys

PROBE = """
import sys
import runefoble_auth.factory
import runefoble_auth.spicedb
import runefoble_auth.sync
loaded = sorted(name for name in sys.modules if name.startswith("runefoble_auth.mock"))
print(",".join(loaded))
"""


def test_production_spicedb_modules_do_not_load_the_mock() -> None:
    result = subprocess.run(
        [sys.executable, "-c", PROBE], capture_output=True, text=True, check=True, timeout=60
    )
    assert result.stdout.strip() == ""
