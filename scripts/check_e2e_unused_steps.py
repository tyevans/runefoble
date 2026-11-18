#!/usr/bin/env python3
"""Fail when an e2e step definition matches no feature step line.

Reads Given/When/Then/Step definitions from e2e/steps and step lines from
e2e/features. Cucumber expression parameters ({string}, {word}, {int},
{float}, {}) are matched the way Cucumber matches them. Outline
placeholders (<name>) are also tried as a plain token, because a feature line
can hold a literal "<tag>" that a step definition matches exactly.

Exit codes: 0 when every definition is used, 1 when a definition is unused,
2 when a definition cannot be parsed or no definitions are found.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFINITION_RE = re.compile(
    r"""^\s*(?:Given|When|Then|Step)\(\s*(?:(['"`])((?:\\.|(?!\1).)*)\1|/((?:\\.|[^/\\\n])+)/[a-z]*)""",
    re.MULTILINE,
)
UNSUPPORTED_DEFINITION_RE = re.compile(
    r"""^\s*(?:Given|When|Then|Step)\((?!\s*['"`/])""", re.MULTILINE
)
STEP_LINE_RE = re.compile(r"^\s*(?:Given|When|Then|And|But|\*)\s+(.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
PARAMETER_RE = re.compile(r"\{(\w*)\}")
PARAMETER_PATTERNS = {
    "string": r"""(?:"[^"]*"|'[^']*')""",
    "word": r"\S+",
    "int": r"[+-]?\d+",
    "float": r"[+-]?\d*\.?\d+",
    "": r".+?",
}


@dataclass(frozen=True)
class Definition:
    path: Path
    line: int
    expression: str
    pattern: re.Pattern[str]


def regex_literal_to_pattern(body: str) -> re.Pattern[str]:
    return re.compile("^(?:" + body + ")$")


def expression_to_pattern(expression: str) -> re.Pattern[str]:
    parts = []
    position = 0
    for match in PARAMETER_RE.finditer(expression):
        parts.append(re.escape(expression[position : match.start()]))
        parts.append(PARAMETER_PATTERNS.get(match.group(1), r".+?"))
        position = match.end()
    parts.append(re.escape(expression[position:]))
    return re.compile("^" + "".join(parts) + "$")


def unescape(literal: str) -> str:
    return re.sub(r"\\(.)", r"\1", literal)


def collect_definitions(steps_dir: Path) -> tuple[list[Definition], list[str]]:
    definitions: list[Definition] = []
    errors: list[str] = []
    for path in sorted(steps_dir.rglob("*.ts")):
        text = path.read_text(encoding="utf-8")
        for match in UNSUPPORTED_DEFINITION_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{path}:{line}: step expression must be a string or regex literal")
        for match in DEFINITION_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            if match.group(3) is not None:
                expression = f"/{match.group(3)}/"
                pattern = regex_literal_to_pattern(match.group(3))
            else:
                expression = unescape(match.group(2))
                pattern = expression_to_pattern(expression)
            definitions.append(Definition(path, line, expression, pattern))
    return definitions, errors


def collect_step_lines(features_dir: Path) -> list[str]:
    lines: list[str] = []
    for path in sorted(features_dir.rglob("*.feature")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            match = STEP_LINE_RE.match(raw)
            if match:
                text = match.group(1)
                lines.append(text)
                lines.append(PLACEHOLDER_RE.sub("x", text))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--steps-dir", type=Path, default=REPO_ROOT / "e2e" / "steps")
    parser.add_argument("--features-dir", type=Path, default=REPO_ROOT / "e2e" / "features")
    args = parser.parse_args(argv)

    definitions, errors = collect_definitions(args.steps_dir)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    if not definitions:
        print(f"error: no step definitions found in {args.steps_dir}", file=sys.stderr)
        return 2

    step_lines = collect_step_lines(args.features_dir)
    unused = [d for d in definitions if not any(d.pattern.match(step) for step in step_lines)]
    for definition in unused:
        print(
            f'{definition.path}:{definition.line}: unused step definition "{definition.expression}"'
        )
    if unused:
        print(f"{len(unused)} unused step definition(s) of {len(definitions)}", file=sys.stderr)
        return 1
    print(f"all {len(definitions)} step definitions are used")
    return 0


if __name__ == "__main__":
    sys.exit(main())
