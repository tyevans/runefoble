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

import pytest

from tests.helpers.frontend_suite import run_frontend_suite


@pytest.mark.timeout(600)
def test_frontend_node_unit_and_integration_test_suite_passes() -> None:
    """Execute frontend test runner verifying plugin lifecycle, event isolation, and token bridge."""
    result = run_frontend_suite()
    assert result.returncode == 0, (
        f"Frontend test runner failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "PluginRegistry Lifecycle & Slot Filtering" in result.stdout
    assert "PluginSandbox CSS Token Bridge & Event Isolation" in result.stdout
    assert "RunefoblePluginSlot Component Contract & Defaults" in result.stdout
