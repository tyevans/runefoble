"""Arithmetic and dice expression interpreter for declarative dynamic tool handlers.

A parsed tree is walked by an allow-list interpreter. Caller text is never
compiled, evaluated, or executed (ADR-0020).
"""

from __future__ import annotations

import ast
import operator
import random
import re
from collections.abc import Callable, Mapping
from typing import Any

MAX_EXPRESSION_CHARS = 200
MAX_EXPRESSION_NODES = 64
MAX_CONSTANT = 10**9
MAX_DICE = 100
MAX_SIDES = 1000
MAX_MODIFIER = 10**6

_BINARY: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_FUNCTIONS: dict[str, Callable[..., Any]] = {"max": max, "min": min, "abs": abs, "round": round}
_DICE = re.compile(r"^(?P<count>\d{1,3})d(?P<sides>\d{1,4})(?P<mod>[+-]\d{1,7})?$")


class HandlerError(ValueError):
    """A handler is invalid at registration or fails at execution."""


def parse_expression(text: str, names: frozenset[str] | None) -> ast.Expression:
    """Parse an expression and refuse every construct outside the allow-list.

    With `names` set, every variable must be in it. With `None`, names are checked at run time.
    """
    if not isinstance(text, str) or not text.strip():
        raise HandlerError("$expr must be a non-blank string")
    if len(text) > MAX_EXPRESSION_CHARS:
        raise HandlerError(f"$expr is longer than {MAX_EXPRESSION_CHARS} characters")
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise HandlerError(f"Invalid $expr '{text}': {exc}") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_EXPRESSION_NODES:
        raise HandlerError(f"$expr has more than {MAX_EXPRESSION_NODES} elements")
    for node in nodes:
        _check_node(node, names)
    return tree


def _check_node(node: ast.AST, names: frozenset[str] | None) -> None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise HandlerError("$expr allows number constants only")
        if abs(node.value) > MAX_CONSTANT:
            raise HandlerError("$expr constant is too large")
    elif isinstance(node, ast.Name):
        if node.id not in _FUNCTIONS and names is not None and node.id not in names:
            raise HandlerError(f"$expr uses '{node.id}', which is not a declared parameter")
    elif isinstance(node, ast.BinOp):
        if type(node.op) not in _BINARY:
            raise HandlerError(f"$expr operator {type(node.op).__name__} is not allowed")
    elif isinstance(node, ast.UnaryOp):
        if type(node.op) not in _UNARY:
            raise HandlerError(f"$expr operator {type(node.op).__name__} is not allowed")
    elif isinstance(node, ast.Call):
        if not (isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS) or node.keywords:
            raise HandlerError("$expr may call max, min, abs, and round with positional arguments")
    elif not isinstance(node, ast.Expression | ast.operator | ast.unaryop | ast.Load):
        raise HandlerError(f"$expr element {type(node).__name__} is not allowed")


def evaluate_expression(tree: ast.Expression, arguments: Mapping[str, Any]) -> int | float:
    """Evaluate a parsed, checked expression against tool arguments."""
    try:
        return _walk(tree.body, arguments)
    except ZeroDivisionError as exc:
        raise HandlerError(f"Arithmetic error: {exc}") from exc
    except (TypeError, OverflowError) as exc:
        raise HandlerError(f"Arithmetic error: {exc}") from exc


def _walk(node: ast.AST, arguments: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        value = arguments.get(node.id)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise HandlerError(f"Argument '{node.id}' must be a number in $expr")
        return value
    if isinstance(node, ast.BinOp):
        return _BINARY[type(node.op)](_walk(node.left, arguments), _walk(node.right, arguments))
    if isinstance(node, ast.UnaryOp):
        return _UNARY[type(node.op)](_walk(node.operand, arguments))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return _FUNCTIONS[node.func.id](*(_walk(arg, arguments) for arg in node.args))
    raise HandlerError("Unsupported $expr element")


def parse_dice(text: str) -> tuple[int, int, int]:
    """Parse 'NdS' with an optional signed modifier into (count, sides, modifier)."""
    match = _DICE.match(text.strip()) if isinstance(text, str) else None
    if match is None:
        raise HandlerError(f"Invalid $dice '{text}': use NdS, NdS+M, or NdS-M")
    count, sides = int(match["count"]), int(match["sides"])
    modifier = int(match["mod"] or 0)
    if not 1 <= count <= MAX_DICE or not 1 <= sides <= MAX_SIDES or abs(modifier) > MAX_MODIFIER:
        raise HandlerError(
            f"$dice '{text}' is outside the limits ({MAX_DICE} dice, {MAX_SIDES} sides)"
        )
    return count, sides, modifier


def roll_dice(spec: tuple[int, int, int], rng: random.Random) -> int:
    count, sides, modifier = spec
    return sum(rng.randint(1, sides) for _ in range(count)) + modifier
