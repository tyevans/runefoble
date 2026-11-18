"""Blackbox test for the single spec-ops pin (TASK-0700).

The pin lives in one place: the `SPEC_OPS_SOURCE` variable in the Makefile.
`make install-spec-ops` installs the pinned CLI. CI and the developer
docs call that target. The test runs `make -n` and checks the printed command.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_OPS_COMMIT = "2c8d073180eb558a57aeb500ffcc6210361c8ee7"


def test_make_install_spec_ops_installs_the_pinned_commit() -> None:
    result = subprocess.run(
        ["make", "-n", "install-spec-ops"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    expected = (
        f"uv tool install --from git+https://github.com/tyevans/spec-ops@{SPEC_OPS_COMMIT} spec-ops"
    )
    assert expected in result.stdout


def test_make_install_spec_ops_ignores_command_line_override() -> None:
    result = subprocess.run(
        ["make", "-n", "install-spec-ops", "SPEC_OPS_SOURCE=git+https://example.invalid/other"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert f"@{SPEC_OPS_COMMIT}" in result.stdout
    assert "example.invalid" not in result.stdout
