"""Reads the App Shell source for source-level wiring checks (TASK-0640b).

The App Shell is split between runefoble-app.ts and the modules in src/app/.
Wiring checks read both, so they assert on the shell as a whole.
"""

from pathlib import Path


def read_app_shell_source(app_ts: Path) -> str:
    """Return runefoble-app.ts followed by every module in its sibling app/ directory."""
    files = [app_ts, *sorted((app_ts.parent / "app").glob("*.ts"))]
    return "\n".join(f.read_text(encoding="utf-8") for f in files)
