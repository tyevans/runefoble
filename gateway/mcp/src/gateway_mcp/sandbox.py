"""Execution sandbox and AST static analysis security policies for dynamic MCP tools.

Enforces strict isolation by forbidding dangerous imports, calls, and dunder attributes.
Governed by ADR-0008 (FastMCP Gateway Architecture).
"""

from __future__ import annotations

import ast
import json
import logging
import math
import random
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("runefoble.gateway_mcp.sandbox")

# Disallowed modules, builtins, and attribute accesses for sandboxed code execution
FORBIDDEN_MODULES: frozenset[str] = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "urllib",
        "requests",
        "httpx",
        "pathlib",
        "builtins",
        "importlib",
        "pickle",
        "ctypes",
        "inspect",
        "multiprocessing",
        "threading",
        "signal",
        "pty",
        "commands",
    }
)

FORBIDDEN_CALLS: frozenset[str] = frozenset(
    {
        "open",
        "eval",
        "exec",
        "compile",
        "__import__",
        "globals",
        "locals",
        "breakpoint",
        "input",
        "exit",
        "quit",
        "memoryview",
    }
)

FORBIDDEN_ATTRS: frozenset[str] = frozenset(
    {
        "__class__",
        "__subclasses__",
        "__globals__",
        "__code__",
        "__builtins__",
        "__import__",
        "__dict__",
    }
)

SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "Exception": Exception,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "KeyError": KeyError,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "TypeError": TypeError,
    "ValueError": ValueError,
    "zip": zip,
    "None": None,
    "True": True,
    "False": False,
}


def validate_sandbox_code(code_str: str) -> None:
    """Perform AST static analysis to reject unsafe imports, calls, and dunder attributes."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError as exc:
        raise ValueError(f"Syntax error in handler_code: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_name = alias.name.split(".")[0]
                if mod_name in FORBIDDEN_MODULES:
                    raise ValueError(
                        f"Sandbox policy violation: importing '{mod_name}' is forbidden"
                    )
        elif isinstance(node, ast.ImportFrom):
            mod_name = (node.module or "").split(".")[0]
            if mod_name in FORBIDDEN_MODULES:
                raise ValueError(
                    f"Sandbox policy violation: importing from '{mod_name}' is forbidden"
                )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FORBIDDEN_CALLS
        ):
            raise ValueError(f"Sandbox policy violation: invoking '{node.func.id}()' is forbidden")
        elif isinstance(node, ast.Attribute) and (
            node.attr in FORBIDDEN_ATTRS or node.attr.startswith("__")
        ):
            raise ValueError(
                f"Sandbox policy violation: attribute access '{node.attr}' is forbidden"
            )


def execute_sandboxed_handler(code_str: str, args: dict[str, Any]) -> Any:
    """Execute handler code inside a restricted execution namespace."""
    validate_sandbox_code(code_str)
    safe_globals: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "math": math,
        "json": json,
        "re": re,
        "random": random,
    }
    local_ns: dict[str, Any] = {}
    exec(code_str, safe_globals, local_ns)

    handler_fn: Callable[..., Any] | None = None
    if "handle" in local_ns and callable(local_ns["handle"]):
        handler_fn = local_ns["handle"]
    else:
        for val in local_ns.values():
            if callable(val):
                handler_fn = val
                break

    if not handler_fn:
        raise ValueError("handler_code must define at least one callable function (e.g. 'handle')")

    return handler_fn(**args)
