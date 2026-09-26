"""Client asset loader and bundler for Runefoble Project Content Visualizer."""

from __future__ import annotations

from pathlib import Path

_STATIC_JS_DIR = Path(__file__).resolve().parent / "static" / "js"
_MODULE_ORDER = [
    "core.js",
    "drawer.js",
    "kanban.js",
    "gantt.js",
    "graph_physics.js",
    "graph.js",
    "traceability.js",
    "roadmap.js",
    "entities.js",
]


def get_client_js() -> str:
    """Concatenate and return modular client JavaScript assets."""
    parts: list[str] = []
    seen: set[str] = set()
    for mod_name in _MODULE_ORDER:
        mod_file = _STATIC_JS_DIR / mod_name
        if mod_file.exists():
            parts.append(f"// --- {mod_name} ---\n" + mod_file.read_text(encoding="utf-8"))
            seen.add(mod_name)
    # Include any remaining .js files dynamically
    for extra_file in sorted(_STATIC_JS_DIR.glob("*.js")):
        if extra_file.name not in seen:
            parts.append(f"// --- {extra_file.name} ---\n" + extra_file.read_text(encoding="utf-8"))
            seen.add(extra_file.name)
    return "\n\n".join(parts)
