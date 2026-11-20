"""Record a pushed image digest in the hosted image values file (TASK-0960).

`make images-push` calls this once per pushed image. It replaces the one `image:` line for the
runefoble image with the full reference `<registry>/runefoble/<name>:<version>@<digest>`.

Usage: python3 scripts/record_image_digests.py VALUES_FILE NAME REGISTRY VERSION DIGEST
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")


def record(values_file: Path, name: str, registry: str, version: str, digest: str) -> str:
    """Replace the runefoble image line for `name` and return the new reference."""
    if DIGEST_RE.fullmatch(digest) is None:
        raise ValueError(f"not a sha256 digest: {digest!r}")
    reference = f"{registry.rstrip('/')}/runefoble/{name}:{version}@{digest}"
    line_re = re.compile(
        rf"^(\s*image:\s*)\S*runefoble/{re.escape(name)}:{re.escape(version)}(?:@\S+)?\s*$",
        re.MULTILINE,
    )
    text = values_file.read_text(encoding="utf-8")
    new_text, count = line_re.subn(lambda match: match.group(1) + reference, text)
    if count != 1:
        raise ValueError(f"expected one image line for runefoble/{name}, found {count}")
    values_file.write_text(new_text, encoding="utf-8")
    return reference


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    values_file, name, registry, version, digest = argv
    try:
        reference = record(Path(values_file), name, registry, version, digest)
    except ValueError as exc:
        print(f"record_image_digests: {exc}", file=sys.stderr)
        return 1
    print(f"Recorded {reference} in {values_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
