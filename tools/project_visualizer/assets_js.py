"""Client asset loader and bundler for Runefoble Project Content Visualizer."""

from __future__ import annotations

from pathlib import Path

_STATIC_JS_DIR = Path(__file__).resolve().parent / "static" / "js"
_MODULE_ORDER = [
    "core.js",
    "markdown.js",
    "drawer/task_card.js",
    "drawer/adr_card.js",
    "drawer/prd_card.js",
    "drawer/persona_card.js",
    "drawer/controller.js",
    "drawer.js",
    "kanban.js",
    "gantt.js",
    "graph_physics.js",
    "graph.js",
    "graph_camera.js",
    "traceability.js",
    "roadmap.js",
    "entities.js",
]

_LIVE_ONLY_MODULES = [
    "agy_launcher.js",
]


def get_client_js(is_live_server: bool = False) -> str:
    """Concatenate and return modular client JavaScript assets.

    In static distribution mode (is_live_server=False), interactive agent runners
    like agy_launcher.js are strictly excluded to avoid leaking development tooling
    into published static documentation for GitHub Pages.
    """
    parts: list[str] = []
    seen: set[str] = set()

    order = list(_MODULE_ORDER)
    if is_live_server:
        order.extend(_LIVE_ONLY_MODULES)

    for mod_name in order:
        mod_file = _STATIC_JS_DIR / mod_name
        if mod_file.exists():
            parts.append(f"// --- {mod_name} ---\n" + mod_file.read_text(encoding="utf-8"))
            seen.add(mod_name)

    # Include any remaining .js files dynamically (filtering live-only modules when not in live server mode)
    for extra_file in sorted(_STATIC_JS_DIR.rglob("*.js")):
        rel_posix = extra_file.relative_to(_STATIC_JS_DIR).as_posix()
        if extra_file.name in _LIVE_ONLY_MODULES and not is_live_server:
            continue
        if rel_posix not in seen and extra_file.name not in seen:
            parts.append(f"// --- {rel_posix} ---\n" + extra_file.read_text(encoding="utf-8"))
            seen.add(rel_posix)
    return "\n\n".join(parts)
