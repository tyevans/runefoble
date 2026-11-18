"""Load a service microfrontend manifest. A missing or invalid manifest is a start-up error.

ADR-0013: the manifest is the contract for the App Shell. ADR-0015 (4): a broken
manifest must not fall back to hardcoded data. Run as a module to check manifests in
the build: `python -m runefoble_platform.ui_manifest <manifest.json>...`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class UIManifestError(RuntimeError):
    """Raised when a service cannot read its UI manifest."""


def load_ui_manifest(path: Path) -> dict[str, Any]:
    """Return the manifest object at `path`. Raise UIManifestError when it is unusable."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise UIManifestError(
            f"UI manifest not found: {path}. Build the service UI package to create it."
        ) from exc
    except OSError as exc:
        raise UIManifestError(f"UI manifest is unreadable: {path}: {exc}") from exc
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UIManifestError(f"UI manifest is not valid JSON: {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise UIManifestError(f"UI manifest must be a JSON object: {path}")
    return manifest


def main(argv: list[str]) -> int:
    """Check each manifest path. Print each failure and return a non-zero status."""
    status = 0
    for raw_path in argv:
        try:
            load_ui_manifest(Path(raw_path))
        except UIManifestError as exc:
            print(exc, file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
