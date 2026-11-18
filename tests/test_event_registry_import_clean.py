"""Importing the event registry must not emit warnings.

eventsource-py logs a warning at class definition time when an explicit
``event_type`` differs from the class name. A clean import proves every
wire type is declared without that warning.
"""

from __future__ import annotations

import os
import sys

from tests.helpers.process import run_command


def test_importing_runefoble_events_emits_no_warnings() -> None:
    env = {**os.environ, "PYTHONWARNINGS": "error"}
    result = run_command(
        [sys.executable, "-c", "import runefoble_events"], env=env, timeout=120, check=False
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
