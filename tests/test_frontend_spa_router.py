"""Blackbox tests for Frontend SPA Client Router and Breadcrumb Navigation Chrome.

Governing ADRs: ADR-0004, ADR-0012, ADR-0013.
Task Reference: TASK-0206.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
ROUTER_TS = FRONTEND_DIR / "src" / "router" / "router.ts"
ROUTER_INDEX_TS = FRONTEND_DIR / "src" / "router" / "index.ts"
BREADCRUMBS_TS = FRONTEND_DIR / "src" / "components" / "runefoble-breadcrumbs.ts"
STORIES_TS = FRONTEND_DIR / "src" / "stories" / "runefoble-breadcrumbs.stories.ts"
HEADER_TS = FRONTEND_DIR / "src" / "components" / "runefoble-header.ts"
APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
INDEX_TS = FRONTEND_DIR / "src" / "index.ts"
TEST_ROUTER_TS = FRONTEND_DIR / "test" / "router.test.ts"


def test_file_length_limits_and_structure():
    """Verify Hard Invariant 6: Decomposed files strictly satisfy line count constraints."""
    assert ROUTER_TS.is_file(), f"{ROUTER_TS} must exist"
    assert BREADCRUMBS_TS.is_file(), f"{BREADCRUMBS_TS} must exist"
    assert STORIES_TS.is_file(), f"{STORIES_TS} must exist"
    assert ROUTER_INDEX_TS.is_file(), f"{ROUTER_INDEX_TS} must exist"

    router_lines = len(ROUTER_TS.read_text(encoding="utf-8").splitlines())
    breadcrumbs_lines = len(BREADCRUMBS_TS.read_text(encoding="utf-8").splitlines())
    header_lines = len(HEADER_TS.read_text(encoding="utf-8").splitlines())
    app_lines = len(APP_TS.read_text(encoding="utf-8").splitlines())

    assert router_lines < 250, f"router.ts has {router_lines} lines (expected < 250)"
    assert breadcrumbs_lines < 180, (
        f"runefoble-breadcrumbs.ts has {breadcrumbs_lines} lines (expected < 180)"
    )
    assert header_lines < 250, f"runefoble-header.ts has {header_lines} lines (expected < 250)"
    assert app_lines < 250, f"runefoble-app.ts has {app_lines} lines (expected < 250)"


def test_spa_router_declarations_and_api():
    """Verify router declares standard deep-linkable route patterns, guards, and teardown lifecycle."""
    content = ROUTER_TS.read_text(encoding="utf-8")

    # Standard routes
    expected_routes = [
        "#/login",
        "#/register",
        "#/campaigns",
        "#/campaigns/:campaignId",
        "#/campaigns/:campaignId/characters",
        "#/campaigns/:campaignId/lobby/:sessionId",
        "#/campaigns/:campaignId/sessions/:sessionId",
        "#/characters",
        "#/profile",
    ]
    for route in expected_routes:
        assert route in content, f"Standard route {route} must be declared in router.ts"

    # API surface
    assert "class Router" in content
    assert "addRoute(" in content
    assert "beforeEach(" in content
    assert "onRouteChanged(" in content
    assert "registerTeardown(" in content
    assert "setTitleResolver(" in content
    assert "setAsyncTitleResolver(" in content
    assert "setRouteTitle(" in content
    assert "resolveTitle(" in content
    assert "resolveTitleAsync(" in content
    assert "match(" in content
    assert "navigate(" in content
    assert "teardownCurrentRoute(" in content
    assert "export const router = Router.getInstance()" in content


def test_breadcrumbs_component_markup_and_bauhaus_tokens():
    """Verify runefoble-breadcrumbs Lit component structure, semantics, and Bauhaus design tokens."""
    content = BREADCRUMBS_TS.read_text(encoding="utf-8")

    assert "@customElement('runefoble-breadcrumbs')" in content
    assert "export class RunefobleBreadcrumbs extends LitElement" in content
    assert "items: BreadcrumbItem[]" in content
    assert "separator = '›'" in content
    assert 'aria-label="Breadcrumb"' in content
    assert 'aria-current="page"' in content
    assert "'breadcrumb-click'" in content

    # Bauhaus styling tokens
    assert "--rf-font-family" in content
    assert "--rf-accent-primary" in content
    assert "--rf-border-width" in content
    assert "--rf-border-color" in content
    assert "--rf-shadow-sm" in content


def test_breadcrumbs_storybook_stories_coverage():
    """Verify Storybook stories cover root, campaign, lobby, session, and dark mode hierarchies."""
    content = STORIES_TS.read_text(encoding="utf-8")

    assert "CampaignDashboard" in content
    assert "CampaignDetails" in content
    assert "PreGameLobby" in content
    assert "ActiveSession" in content
    assert "DarkModeActiveSession" in content
    assert "CustomSlashSeparator" in content


def test_barrel_exports_and_header_integration():
    """Verify index.ts exports router and breadcrumbs, and header integrates breadcrumbs."""
    index_content = INDEX_TS.read_text(encoding="utf-8")
    assert "export * from './components/runefoble-breadcrumbs.ts';" in index_content
    assert "export * from './router/index.ts';" in index_content

    header_content = HEADER_TS.read_text(encoding="utf-8")
    assert "<runefoble-breadcrumbs" in header_content
    assert ".items=${this.breadcrumbs}" in header_content


def test_typescript_router_unit_test_suite_execution():
    """Execute the Node-based TypeScript router unit test suite."""
    import re

    assert TEST_ROUTER_TS.is_file()
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(TEST_ROUTER_TS.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Router tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    match = re.search(r"pass (\d+)", result.stdout)
    assert match is not None, f"Could not find pass count in output: {result.stdout}"
    assert int(match.group(1)) >= 14, f"Expected at least 14 passed tests, got {match.group(1)}"
    assert "fail 0" in result.stdout


def test_vite_proxy_configuration():
    """Verify frontend/vite.config.ts configures reverse proxy for /api/v1 and /ws."""
    vite_config_path = FRONTEND_DIR / "vite.config.ts"
    assert vite_config_path.is_file()
    content = vite_config_path.read_text(encoding="utf-8")
    assert "'/api/v1'" in content
    assert "'/ws'" in content
    assert "GATEWAY_API_URL" in content
    assert "changeOrigin: true" in content
    assert "ws: true" in content
