"""Blackbox TDD Suite for Profile Settings View & Campaign Creation Idempotency.

Governing ADRs: ADR-0001, ADR-0004, ADR-0007, ADR-0012, ADR-0013.
Task Reference: TASK-0257.
"""

import subprocess
from pathlib import Path

from tests.helpers.zitadel_auth import auth_environment, create_signed_token

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
TS_TEST_FILE = FRONTEND_DIR / "test" / "profile-and-campaign-creation.test.ts"

__all__ = ["auth_environment"]


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
