#!/usr/bin/env python3
"""Find two classes of Lit template defects in UI sources (TASK-0904).

1. Attribute names. Lit observes the attribute that `attribute:` names. Without it, Lit
   observes the lower-case property name: `campaignId` observes `campaignid`, not
   `campaign-id`. The gate fails when a template, an HTML string or a `setAttribute` call
   sets a kebab-case attribute on a Runefoble element, the camelCase form of the name is
   a `@property` of that element, and the property does not observe that attribute.
2. SVG templates. Lit parses an `html` template in the HTML namespace. SVG children such
   as `<g>`, `<circle>` or `<text>` in an `html` template do not render. The gate fails
   when an `html` template starts with an SVG-only element. Use the `svg` tag instead.

The gate reads element definitions from `frontend/src`, `services/*/ui/src` and
`libs/*/src`. It reads usages from these folders and from the UI test folders.

Exit codes: 0 when no defect is found, 1 when a defect is found.
"""

import argparse
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFINITION_GLOBS = ("frontend/src", "services/*/ui/src", "libs/*/src")
USAGE_GLOBS = DEFINITION_GLOBS + (
    "frontend/test",
    "frontend/test-dom",
    "services/*/ui/test",
    "services/*/ui/test-dom",
    "libs/*/test",
    "libs/*/test-dom",
)
EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".mjs"})
SKIP_PARTS = frozenset({"node_modules", "dist", "storybook-static"})

# SVG elements that have no HTML element of the same name. `a`, `style`, `title`,
# `script` and `svg` are left out: they are valid at the start of an `html` template.
SVG_ONLY_TAGS = frozenset(
    {
        "animate",
        "animateMotion",
        "animateTransform",
        "circle",
        "clipPath",
        "defs",
        "desc",
        "ellipse",
        "feBlend",
        "feColorMatrix",
        "feComposite",
        "feGaussianBlur",
        "feMerge",
        "feMergeNode",
        "feOffset",
        "filter",
        "foreignObject",
        "g",
        "line",
        "linearGradient",
        "marker",
        "mask",
        "path",
        "pattern",
        "polygon",
        "polyline",
        "radialGradient",
        "rect",
        "stop",
        "symbol",
        "text",
        "textPath",
        "tspan",
        "use",
    }
)

CUSTOM_ELEMENT_RE = re.compile(r"@customElement\(\s*['\"]([a-z][\w-]*-[\w-]*)['\"]\s*\)")
DEFINE_RE = re.compile(r"customElements\.define\(\s*['\"]([a-z][\w-]*-[\w-]*)['\"]\s*,\s*(\w+)")
CLASS_RE = re.compile(r"\bclass\s+(\w+)(?:\s+extends\s+([\w.]+))?")
PROPERTY_RE = re.compile(r"@property\(")
MEMBER_RE = re.compile(
    r"\s*(?:(?:declare|public|private|protected|readonly|override|accessor|static)\s+)*(\w+)"
)
ATTRIBUTE_OPTION_RE = re.compile(r"\battribute\s*:\s*(?:['\"]([^'\"]+)['\"]|(false|true))")
SET_ATTRIBUTE_RE = re.compile(r"\.setAttribute\(\s*['\"]([a-z][\w-]*)['\"]")
HTML_TAG_RE = re.compile(r"(?<![\w.$])html\s*`")
ATTRIBUTE_NAME_RE = re.compile(r"(?:^|\s)([.?@]?[A-Za-z_:][\w:.-]*)")
FIRST_TAG_RE = re.compile(r"\s*<([A-Za-z][\w-]*)")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str


@dataclass
class ElementClass:
    name: str
    base: str | None
    # property name -> observed attribute name, or None when `attribute: false`.
    properties: dict[str, str | None]


def iter_files(root: Path, globs: tuple[str, ...]) -> Iterator[Path]:
    seen: set[Path] = set()
    for pattern in globs:
        for base in sorted(root.glob(pattern)):
            for path in sorted(base.rglob("*")):
                if path in seen or path.suffix not in EXTENSIONS or not path.is_file():
                    continue
                if SKIP_PARTS.intersection(path.relative_to(root).parts):
                    continue
                seen.add(path)
                yield path


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def balanced_end(text: str, start: int, open_char: str, close_char: str) -> int:
    """Return the offset after the bracket that closes the bracket at `start`."""
    depth = 0
    quote: str | None = None
    index = start
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 1
            elif char == quote:
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(text)


def kebab_to_camel(name: str) -> str:
    head, *rest = name.split("-")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def parse_classes(text: str) -> dict[str, ElementClass]:
    classes: dict[str, ElementClass] = {}
    matches = list(CLASS_RE.finditer(text))
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        properties: dict[str, str | None] = {}
        for decorator in PROPERTY_RE.finditer(body):
            options_end = balanced_end(body, decorator.end() - 1, "(", ")")
            options = body[decorator.end() : options_end - 1]
            member = MEMBER_RE.match(body, options_end)
            if not member:
                continue
            name = member.group(1)
            option = ATTRIBUTE_OPTION_RE.search(options)
            if option is None or option.group(2) == "true":
                properties[name] = name.lower()
            elif option.group(2) == "false":
                properties[name] = None
            else:
                properties[name] = option.group(1)
        base = match.group(2).split(".")[-1] if match.group(2) else None
        classes[match.group(1)] = ElementClass(match.group(1), base, properties)
    return classes


def element_tag_map(text: str) -> dict[str, str]:
    """Map each tag to its class name for `@customElement` and `customElements.define`."""
    tags: dict[str, str] = {}
    for match in CUSTOM_ELEMENT_RE.finditer(text):
        found = CLASS_RE.search(text, match.end())
        if found:
            tags[match.group(1)] = found.group(1)
    for match in DEFINE_RE.finditer(text):
        tags[match.group(1)] = match.group(2)
    return tags


def collect_elements(root: Path) -> dict[str, dict[str, str | None]]:
    classes: dict[str, ElementClass] = {}
    tags: dict[str, str] = {}
    for path in iter_files(root, DEFINITION_GLOBS):
        text = path.read_text(encoding="utf-8")
        if "class " not in text:
            continue
        classes.update(parse_classes(text))
        tags.update(element_tag_map(text))

    def resolve(name: str, depth: int = 0) -> dict[str, str | None]:
        element = classes.get(name)
        if element is None or depth > 10:
            return {}
        inherited = resolve(element.base, depth + 1) if element.base else {}
        return {**inherited, **element.properties}

    return {tag: resolve(name) for tag, name in tags.items()}


def attribute_problem(tag: str, attribute: str, properties: dict[str, str | None]) -> str | None:
    if "-" not in attribute or attribute.startswith(("data-", "aria-")):
        return None
    if attribute in properties.values():
        return None
    camel = kebab_to_camel(attribute)
    if camel not in properties:
        return None
    observed = properties[camel]
    observed_text = "no attribute (attribute: false)" if observed is None else f"'{observed}'"
    return (
        f"<{tag}> attribute '{attribute}' sets nothing: property '{camel}' observes "
        f"{observed_text}. Add attribute: '{attribute}' or bind .{camel}=${{...}}."
    )


def attribute_names(open_tag: str) -> Iterator[tuple[str, int]]:
    """Yield (name, offset) for each attribute in an opening tag."""
    masked = list(open_tag)
    for match in re.finditer(r"\$\{", open_tag):
        end = balanced_end(open_tag, match.start() + 1, "{", "}")
        for index in range(match.start(), end):
            if masked[index] != "\n":
                masked[index] = " "
    flat = "".join(masked)
    flat = re.sub(r"\"[^\"]*\"|'[^']*'", lambda m: " " * len(m.group(0)), flat)
    for match in ATTRIBUTE_NAME_RE.finditer(flat):
        yield match.group(1), match.start(1)


def open_tag_end(text: str, start: int) -> int:
    index = start
    quote: str | None = None
    while index < len(text):
        char = text[index]
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif text.startswith("${", index):
            index = balanced_end(text, index + 1, "{", "}")
            continue
        elif char == ">":
            return index
        index += 1
    return len(text)


def check_tag_usages(
    relative: str, text: str, elements: dict[str, dict[str, str | None]]
) -> Iterator[Finding]:
    if not elements:
        return
    pattern = re.compile(
        r"<("
        + "|".join(re.escape(t) for t in sorted(elements, key=len, reverse=True))
        + r")(?=[\s/>])"
    )
    for match in pattern.finditer(text):
        tag = match.group(1)
        end = open_tag_end(text, match.end())
        open_tag = text[match.end() : end]
        for name, offset in attribute_names(open_tag):
            if name[0] in ".@":
                continue
            problem = attribute_problem(tag, name.lstrip("?"), elements[tag])
            if problem:
                yield Finding(relative, line_of(text, match.end() + offset), problem)


def check_set_attribute(
    relative: str, text: str, elements: dict[str, dict[str, str | None]]
) -> Iterator[Finding]:
    referenced = [tag for tag in elements if tag in text]
    for match in SET_ATTRIBUTE_RE.finditer(text):
        attribute = match.group(1)
        if any(attribute in elements[tag].values() for tag in referenced):
            continue
        problems = (attribute_problem(tag, attribute, elements[tag]) for tag in referenced)
        problem = next((p for p in problems if p), None)
        if problem:
            yield Finding(relative, line_of(text, match.start()), f"setAttribute: {problem}")


def check_svg_in_html(relative: str, text: str) -> Iterator[Finding]:
    for match in HTML_TAG_RE.finditer(text):
        first = FIRST_TAG_RE.match(text, match.end())
        if first and first.group(1) in SVG_ONLY_TAGS:
            yield Finding(
                relative,
                line_of(text, first.start(1)),
                f"html template starts with SVG element <{first.group(1)}>, which does not "
                "render in the HTML namespace. Use the svg tag from 'lit'.",
            )


def scan(root: Path) -> list[Finding]:
    elements = collect_elements(root)
    findings: list[Finding] = []
    for path in iter_files(root, USAGE_GLOBS):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        findings.extend(check_tag_usages(relative, text, elements))
        findings.extend(check_set_attribute(relative, text, elements))
        findings.extend(check_svg_in_html(relative, text))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    findings = scan(args.root.resolve())
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.message}")
    if findings:
        print(f"\nLit template gate failed: {len(findings)} defect(s).")
        return 1
    print("Lit template gate passed: no attribute or SVG template defects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
