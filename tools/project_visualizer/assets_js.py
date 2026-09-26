"""Client asset loader and bundler for Runefoble Project Content Visualizer."""

from __future__ import annotations

from pathlib import Path

_STATIC_JS_DIR = Path(__file__).resolve().parent / "static" / "js"
_MODULE_ORDER = [
    "core.js",
    "drawer.js",
    "kanban.js",
    "gantt.js",
    "graph.js",
    "traceability.js",
    "roadmap.js",
    "entities.js",
]


def get_client_js() -> str:
    """Concatenate and return modular client JavaScript assets."""
    parts: list[str] = []
    for mod_name in _MODULE_ORDER:
        mod_file = _STATIC_JS_DIR / mod_name
        if mod_file.exists():
            parts.append(f"// --- {mod_name} ---\n" + mod_file.read_text(encoding="utf-8"))
    return "\n\n".join(parts)
