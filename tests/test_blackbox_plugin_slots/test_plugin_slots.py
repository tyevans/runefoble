"""Blackbox TDD frontdoor test suite for Community Plugin UI Extension Slots Microfrontend.

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- PRD-0022: Extensible Modder Platform, Universal VTT Asset Bridge & FastMCP Tool Registry
- US-0035: Runtime MCP Tool Hot-Reloading and Web Component Extension Slots
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_PLUGINS_DIR = REPO_ROOT / "frontend" / "src" / "components" / "plugins"
STORIES_FILE = REPO_ROOT / "frontend" / "src" / "stories" / "runefoble-plugin-slot.stories.ts"


def test_plugin_microfrontend_file_limits_and_invariants() -> None:
    """Verify strict modular decomposition and line limits (< 150 lines per module)."""
    assert FRONTEND_PLUGINS_DIR.is_dir(), f"{FRONTEND_PLUGINS_DIR} must exist"

    slot_file = FRONTEND_PLUGINS_DIR / "runefoble-plugin-slot.ts"
    registry_file = FRONTEND_PLUGINS_DIR / "plugin_registry.ts"
    sandbox_file = FRONTEND_PLUGINS_DIR / "plugin_sandbox.ts"

    assert slot_file.is_file(), "runefoble-plugin-slot.ts must exist"
    assert registry_file.is_file(), "plugin_registry.ts must exist"
    assert sandbox_file.is_file(), "plugin_sandbox.ts must exist"
    assert STORIES_FILE.is_file(), "runefoble-plugin-slot.stories.ts must exist"

    limits: dict[Path, int] = {
        slot_file: 140,
        registry_file: 120,
        sandbox_file: 110,
        STORIES_FILE: 130,
    }

    for file_path, max_limit in limits.items():
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines <= max_limit, f"{file_path.name} exceeds specific limit: {lines} > {max_limit}"
        assert lines < 150, (
            f"{file_path.name} exceeds global microfrontend invariant: {lines} >= 150"
        )


def test_plugin_slot_custom_element_and_shadow_dom_contract() -> None:
    """Verify Lit custom element declaration, slot identifiers, and fallback rendering."""
    slot_src = (FRONTEND_PLUGINS_DIR / "runefoble-plugin-slot.ts").read_text(encoding="utf-8")

    assert "@customElement('runefoble-plugin-slot')" in slot_src
    assert "class RunefoblePluginSlot extends LitElement" in slot_src
    assert "slotName" in slot_src
    assert "slotId" in slot_src
    assert "orientation" in slot_src
    assert "showFallback" in slot_src
    assert "fallbackText" in slot_src

    # Supported target slots
    assert "hud-widget" in slot_src
    assert "dice-panel" in slot_src
    assert "sidebar-tool" in slot_src

    # Shadow DOM and fallback slot element
    assert '<slot name="fallback">' in slot_src
    assert "plugin-sandbox-container" in slot_src


def test_plugin_registry_and_lifecycle_manager_contract() -> None:
    """Verify PluginRegistry dynamic registration, unregistration, filtering, and subscriptions."""
    registry_src = (FRONTEND_PLUGINS_DIR / "plugin_registry.ts").read_text(encoding="utf-8")

    assert "interface PluginDefinition" in registry_src
    assert "class PluginRegistry" in registry_src
    assert "register(" in registry_src
    assert "unregister(" in registry_src
    assert "getPluginsForSlot(" in registry_src
    assert "getPlugin(" in registry_src
    assert "getAllPlugins(" in registry_src
    assert "subscribe(" in registry_src
    assert "clear(" in registry_src
    assert "export const pluginRegistry = new PluginRegistry();" in registry_src


def test_plugin_sandbox_css_bridge_and_event_isolation() -> None:
    """Verify Bauhaus CSS custom property token bridge and Shadow DOM event isolation."""
    sandbox_src = (FRONTEND_PLUGINS_DIR / "plugin_sandbox.ts").read_text(encoding="utf-8")

    assert "ALLOWED_TOKEN_PREFIXES" in sandbox_src
    assert "'--rf-color-'" in sandbox_src
    assert "'--rf-space-'" in sandbox_src
    assert "'--rf-font-'" in sandbox_src
    assert "'--rf-border-'" in sandbox_src
    assert "'--rf-shadow-'" in sandbox_src
    assert "isAllowedDesignToken(" in sandbox_src

    assert "createSandboxedEvent" in sandbox_src
    assert "instantiatePluginElement" in sandbox_src
    assert "contain: layout style;" in sandbox_src
    assert "isolation: isolate;" in sandbox_src


def test_frontend_barrel_exports_and_app_shell_integration() -> None:
    """Verify exports in plugins barrel index and App Shell extension slot mounting."""
    index_file = FRONTEND_PLUGINS_DIR / "index.ts"
    assert index_file.is_file()
    index_src = index_file.read_text(encoding="utf-8")
    assert "plugin_registry" in index_src
    assert "plugin_sandbox" in index_src
    assert "runefoble-plugin-slot" in index_src

    app_index = REPO_ROOT / "frontend" / "src" / "index.ts"
    assert "components/plugins/index.ts" in app_index.read_text(encoding="utf-8")

    app_shell_src = (REPO_ROOT / "frontend" / "src" / "runefoble-app.ts").read_text(
        encoding="utf-8"
    )
    assert "components/plugins/runefoble-plugin-slot.ts" in app_shell_src
    assert 'runefoble-plugin-slot slot-id="hud-widget"' in app_shell_src
    assert 'runefoble-plugin-slot slot-id="sidebar-tool"' in app_shell_src
    assert 'runefoble-plugin-slot slot-id="dice-panel"' in app_shell_src


def test_storybook_stories_coverage_and_theme_variations() -> None:
    """Verify Storybook stories include Light, Dark, HUD, Dice, Sidebar, and Fallback states."""
    stories_src = STORIES_FILE.read_text(encoding="utf-8")

    assert "title: 'Plugins/RunefoblePluginSlot'" in stories_src
    assert "SidebarToolLight" in stories_src
    assert "SidebarToolDark" in stories_src
    assert "HudWidgetLight" in stories_src
    assert "HudWidgetDark" in stories_src
    assert "DicePanelLight" in stories_src
    assert "DicePanelDark" in stories_src
    assert "FallbackPlaceholder" in stories_src
    assert "data-theme=" in stories_src
    assert "'dark'" in stories_src
    assert "'light'" in stories_src


def test_frontend_node_unit_and_integration_test_suite_passes() -> None:
    """Execute frontend test runner verifying plugin lifecycle, event isolation, and token bridge."""
    result = subprocess.run(
        ["pnpm", "--prefix", "frontend", "test"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Frontend test runner failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "PluginRegistry Lifecycle & Slot Filtering" in result.stdout
    assert "PluginSandbox CSS Token Bridge & Event Isolation" in result.stdout
    assert "RunefoblePluginSlot Component Contract & Defaults" in result.stdout
