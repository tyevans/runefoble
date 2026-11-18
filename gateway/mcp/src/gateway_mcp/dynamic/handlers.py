"""Declarative handler validation and evaluation for dynamic tools (ADR-0020).

A handler is a JSON result template. Strings may hold `${name}` placeholders.
`{"$expr": ...}` and `{"$dice": ...}` objects compute numbers. No caller text
is compiled or run.
"""

from __future__ import annotations

import random
import re
from collections.abc import Mapping
from typing import Any

from gateway_mcp.dynamic.expressions import (
    HandlerError,
    evaluate_expression,
    parse_dice,
    parse_expression,
    roll_dice,
)

MAX_DEPTH = 8
MAX_ITEMS = 200
_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_DIRECTIVES = ("$expr", "$dice")
_rng = random.Random()  # noqa: S311 - game dice, not security


def validate_handler(handler: Any, parameter_names: frozenset[str]) -> None:
    """Refuse a handler that holds an unknown name, an unknown directive, or a limit breach."""
    count = _validate(handler, parameter_names, 0)
    if count > MAX_ITEMS:
        raise HandlerError(f"handler has more than {MAX_ITEMS} elements")


def _validate(node: Any, names: frozenset[str], depth: int) -> int:
    if depth > MAX_DEPTH:
        raise HandlerError(f"handler is nested deeper than {MAX_DEPTH} levels")
    if isinstance(node, str):
        for name in _PLACEHOLDER.findall(node):
            if name not in names:
                raise HandlerError(f"Placeholder '${{{name}}}' is not a declared parameter")
        return 1
    if isinstance(node, list):
        return 1 + sum(_validate(item, names, depth + 1) for item in node)
    if isinstance(node, dict):
        directive_keys = [k for k in node if isinstance(k, str) and k.startswith("$")]
        if directive_keys:
            return _validate_directive(node, directive_keys, names)
        return 1 + sum(_validate(v, names, depth + 1) for v in node.values())
    if node is None or isinstance(node, bool | int | float):
        return 1
    raise HandlerError(f"handler value of type {type(node).__name__} is not allowed")


def _validate_directive(node: dict[str, Any], keys: list[str], names: frozenset[str]) -> int:
    if len(node) != 1 or keys[0] not in _DIRECTIVES:
        raise HandlerError(
            f"A directive object holds exactly one of {', '.join(_DIRECTIVES)}; got {sorted(node)}"
        )
    if keys[0] == "$expr":
        parse_expression(node["$expr"], names)
    else:
        parse_dice(node["$dice"])
    return 1


def evaluate_handler(handler: Any, arguments: Mapping[str, Any]) -> Any:
    """Evaluate a validated handler template against tool arguments."""
    if isinstance(handler, str):
        whole = _PLACEHOLDER.fullmatch(handler)
        if whole:
            return arguments.get(whole.group(1))
        return _PLACEHOLDER.sub(lambda m: str(arguments.get(m.group(1))), handler)
    if isinstance(handler, list):
        return [evaluate_handler(item, arguments) for item in handler]
    if isinstance(handler, dict):
        if "$expr" in handler:
            tree = parse_expression(handler["$expr"], None)
            return evaluate_expression(tree, arguments)
        if "$dice" in handler:
            return roll_dice(parse_dice(handler["$dice"]), _rng)
        return {key: evaluate_handler(value, arguments) for key, value in handler.items()}
    return handler
