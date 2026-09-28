"""Blackbox TDD Suite for Profile Settings View & Campaign Creation Idempotency.

Governing ADRs: ADR-0001, ADR-0004, ADR-0007, ADR-0012, ADR-0013.
Task Reference: TASK-0257.
"""

import subprocess
from pathlib import Path

from tests.helpers.zitadel_auth import auth_environment, create_signed_token

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
ROUTER_TS = FRONTEND_DIR / "src" / "router" / "router.ts"
PROFILE_TS = FRONTEND_DIR / "src" / "components" / "runefoble-user-profile.ts"
PROFILE_STYLES_TS = FRONTEND_DIR / "src" / "components" / "runefoble-user-profile.styles.ts"
USER_MENU_TS = FRONTEND_DIR / "src" / "components" / "runefoble-user-menu.ts"
APP_DATA_SERVICE_TS = FRONTEND_DIR / "src" / "services" / "app-data-service.ts"
APP_DATA_FALLBACKS_TS = FRONTEND_DIR / "src" / "services" / "app-data-fallbacks.ts"
CAMPAIGN_DASHBOARD_TS = (
    REPO_ROOT
    / "services"
    / "game_session"
    / "ui"
    / "src"
    / "campaigns"
    / "runefoble-campaign-dashboard.ts"
)
STORIES_TS = FRONTEND_DIR / "src" / "stories" / "runefoble-user-profile.stories.ts"
TS_TEST_FILE = FRONTEND_DIR / "test" / "profile-and-campaign-creation.test.ts"

__all__ = ["auth_environment"]


def test_file_length_limits_and_decomposition():
    """Verify Hard Invariant 6: All modified and created files strictly satisfy line count constraints (<500 lines)."""
    files_to_check = [
        (PROFILE_TS, 350),
        (PROFILE_STYLES_TS, 300),
        (APP_TS, 300),
        (ROUTER_TS, 250),
        (APP_DATA_SERVICE_TS, 450),
        (APP_DATA_FALLBACKS_TS, 150),
        (CAMPAIGN_DASHBOARD_TS, 350),
        (STORIES_TS, 100),
    ]

    for file_path, max_lines in files_to_check:
        assert file_path.is_file(), f"File {file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{file_path.name} has {lines} lines (expected < {max_lines})"


def test_router_profile_pattern_and_breadcrumb_trail():
    """Verify router declares #/profile route with hierarchical breadcrumbs [Home, Account Settings]."""
    content = ROUTER_TS.read_text(encoding="utf-8")

    assert "'#/profile'" in content
    assert "pattern === '#/profile'" in content
    assert "{ label: 'Home', path: '#/campaigns' }" in content
    assert "{ label: 'Account Settings', path: '#/profile', active: true }" in content


def test_user_menu_account_settings_navigation():
    """Verify runefoble-user-menu routes to #/profile on clicking Account Settings."""
    content = USER_MENU_TS.read_text(encoding="utf-8")

    assert "handleAccountSettings" in content
    assert "router.navigate('#/profile')" in content
    assert "Account Settings" in content


def test_app_shell_profile_view_orchestration():
    """Verify runefoble-app imports runefoble-user-profile, resolves active view 'profile', and mounts component."""
    content = APP_TS.read_text(encoding="utf-8")

    assert "import './components/runefoble-user-profile.ts';" in content
    assert "'profile'" in content

    # getActiveView mapping
    assert "pat === '#/profile'" in content

    # renderActiveView mounting
    assert "<runefoble-user-profile" in content
    assert ".user=${authService.getUser()}" in content
    assert ".currentTheme=${this.currentTheme}" in content
    assert ".currentColorMode=${this.currentColorMode}" in content
    assert "@auth-logout=" in content


def test_user_profile_component_claims_and_controls():
    """Verify runefoble-user-profile renders user profile claims, role badges, theme selection, and logout."""
    content = PROFILE_TS.read_text(encoding="utf-8")
    styles_content = PROFILE_STYLES_TS.read_text(encoding="utf-8")

    assert "@customElement('runefoble-user-profile')" in content
    assert "export class RunefobleUserProfile extends LitElement" in content

    # Claims rendered
    assert "user.username" in content
    assert "user.user_id" in content
    assert "user.email" in content
    assert "user.roles" in content
    assert "user.is_admin" in content or "isAdmin" in content

    # API / Service retrieval
    assert "/api/v1/profile" in content
    assert "authService.getUser()" in content
    assert "authService.logout()" in content
    assert "'auth-logout'" in content

    # Theme and color mode controls
    assert "<runefoble-theme-switcher" in content
    assert "handleThemeChanged" in content
    assert "setColorMode" in content

    # Bauhaus styling tokens in styles
    assert "--rf-bg-surface" in styles_content
    assert "--rf-border-width" in styles_content
    assert "--rf-border-color" in styles_content
    assert "--rf-shadow" in styles_content
    assert "--rf-accent-primary" in styles_content


def test_campaign_dashboard_event_propagation_stopping():
    """Verify runefoble-campaign-dashboard stops propagation of child create-campaign event."""
    content = CAMPAIGN_DASHBOARD_TS.read_text(encoding="utf-8")

    assert "handleCreatorSubmit(e: CustomEvent<CreateCampaignPayload>): void {" in content
    assert "e.stopPropagation();" in content
    assert "this.dispatchEvent(" in content
    assert "'create-campaign'" in content


def test_app_data_service_campaign_deduplication():
    """Verify AppDataService enforces campaign ID uniqueness using Map."""
    content = APP_DATA_SERVICE_TS.read_text(encoding="utf-8")

    assert "deduplicateCampaigns(" in content
    assert "new Map<string, CampaignItem>()" in content
    assert "fetchProfile(" in content
    assert "${this.apiBase}/profile" in content


def test_gateway_profile_rest_endpoint_claims(auth_environment):
    """Verify GET /api/v1/profile public frontdoor returns user claims via FastAPI gateway."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]

    user_id = "user-valeros-test"
    token = create_signed_token(
        valid_key,
        sub=user_id,
        kid=kid,
        roles=["player", "dm"],
        preferred_username="Valeros",
    )

    res = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == user_id
    assert data["username"] == "Valeros"
    assert data["email"] == f"{user_id}@runefoble.local"
    assert "player" in data["roles"]
    assert "dm" in data["roles"]


def test_typescript_unit_test_suite_execution():
    """Execute the Node-based TypeScript test suite for profile and campaign creation idempotency."""
    assert TS_TEST_FILE.is_file()
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(TS_TEST_FILE.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"TypeScript unit tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "pass 5" in result.stdout
    assert "fail 0" in result.stdout
