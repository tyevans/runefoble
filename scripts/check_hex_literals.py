#!/usr/bin/env python3
"""Block new hex colour literals in UI sources outside the theme token files.

UI components must use `var(--rf-*)` design tokens (ADR-0012, ADR-0004, TASK-0763).
The gate scans UI sources under `frontend/src`, `services/*/ui/src` and `libs/*/src`.
Hex literals in the token definition files under `frontend/src/styles/` are allowed.
A hex fallback inside `var(--rf-x, #123456)` counts as a literal.

The baseline file records the permitted count per file. A count can only fall:
the gate fails when a file holds more literals than its baseline entry, and
`--update-baseline` lowers entries but refuses to raise one.

Exit codes: 0 when no file exceeds its baseline, 1 when a file exceeds it (or when
`--update-baseline` would raise an entry), 2 when the baseline file is missing or invalid.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = REPO_ROOT / "scripts" / "hex_baseline.json"

SCAN_GLOBS = ("frontend/src", "services/*/ui/src", "libs/*/src")
EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".mjs", ".css", ".html"})
TOKEN_DEFINITION_FILES = ("frontend/src/styles/themes.css", "frontend/src/styles/themes/*.css")

# A colour is #rgb, #rgba, #rrggbb or #rrggbbaa. The look-behind drops `this.#field`,
# `&#x27;` and `##`. The look-ahead drops ids such as `#add-button`, longer numbers and
# private field declarations such as `#cafe = 1`.
HEX_RE = re.compile(
    r"(?<![\w#&.$])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])(?!\s*[=(])"
)


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    literal: str


class BaselineError(Exception):
    """The baseline file is missing or does not hold a valid `files` mapping."""


def is_token_definition(relative: Path) -> bool:
    return any(relative.match(pattern) for pattern in TOKEN_DEFINITION_FILES)


def iter_sources(root: Path):
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for base in sorted(root.glob(pattern)):
            for path in sorted(base.rglob("*")):
                relative = path.relative_to(root)
                if path in seen or not path.is_file() or path.suffix not in EXTENSIONS:
                    continue
                if is_token_definition(relative):
                    continue
                seen.add(path)
                yield relative


def scan(root: Path) -> dict[str, list[Hit]]:
    hits: dict[str, list[Hit]] = {}
    for relative in iter_sources(root):
        text = (root / relative).read_text(encoding="utf-8")
        key = relative.as_posix()
        for number, line in enumerate(text.splitlines(), start=1):
            for match in HEX_RE.finditer(line):
                hits.setdefault(key, []).append(Hit(key, number, match.group(0)))
    return hits


def load_baseline(path: Path) -> dict[str, int]:
    if not path.is_file():
        raise BaselineError(f"baseline file not found: {path}")
    try:
        files = json.loads(path.read_text(encoding="utf-8"))["files"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise BaselineError(
            f"baseline file {path} has no valid 'files' mapping: {error}"
        ) from error
    if not isinstance(files, dict) or not all(
        isinstance(k, str) and isinstance(v, int) for k, v in files.items()
    ):
        raise BaselineError(f"baseline file {path}: 'files' must map paths to integers")
    return files


def write_baseline(path: Path, counts: dict[str, int]) -> None:
    payload = {"files": dict(sorted(counts.items()))}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def check(hits: dict[str, list[Hit]], baseline: dict[str, int]) -> int:
    failures = 0
    for path, file_hits in sorted(hits.items()):
        allowed = baseline.get(path, 0)
        if len(file_hits) <= allowed:
            continue
        failures += 1
        print(f"{path}: {len(file_hits)} hex literals, baseline allows {allowed}")
        for hit in file_hits:
            print(f"  {hit.path}:{hit.line}: {hit.literal}")
    total = sum(len(file_hits) for file_hits in hits.values())
    if failures:
        print(
            f"\n{failures} file(s) exceed the hex baseline. Use var(--rf-*) tokens. "
            "Define a missing semantic colour in frontend/src/styles/themes/."
        )
        return 1
    lower = sorted(p for p, n in baseline.items() if len(hits.get(p, [])) < n)
    print(f"Hex gate passed: {total} literals in {len(hits)} files, none above the baseline.")
    if lower:
        print(
            f"{len(lower)} file(s) are below the baseline. Run with --update-baseline to lower it."
        )
    return 0


def update(hits: dict[str, list[Hit]], baseline: dict[str, int], path: Path) -> int:
    raised = sorted(p for p, h in hits.items() if len(h) > baseline.get(p, 0))
    if raised:
        for name in raised:
            print(
                f"{name}: {len(hits[name])} hex literals, baseline allows {baseline.get(name, 0)}"
            )
        print("\nThe baseline can only fall. Replace the new hex literals with var(--rf-*) tokens.")
        return 1
    write_baseline(path, {p: len(h) for p, h in hits.items() if h})
    print(f"Baseline updated: {sum(len(h) for h in hits.values())} literals in {len(hits)} files.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--update-baseline", action="store_true", help="lower the baseline to the current counts"
    )
    args = parser.parse_args(argv)
    try:
        baseline = load_baseline(args.baseline)
    except BaselineError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    hits = scan(args.root.resolve())
    if args.update_baseline:
        return update(hits, baseline, args.baseline)
    return check(hits, baseline)


if __name__ == "__main__":
    sys.exit(main())
