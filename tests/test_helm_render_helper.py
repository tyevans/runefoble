"""Blackbox checks for the shared Helm render gate in `tests/helpers/helm.py` (TASK-0869).

The gate decides what a chart test does when helm is not on PATH. A developer machine skips
the test. CI fails it, so a CI host without helm never passes a chart check with no assertion.
"""

from __future__ import annotations

import pytest

from tests.helpers.helm import require_helm


@pytest.fixture
def path_without_helm(tmp_path, monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setenv("PATH", str(tmp_path))
    return monkeypatch


def test_require_helm_fails_in_ci_when_helm_is_missing(path_without_helm, monkeypatch) -> None:
    monkeypatch.setenv("CI", "true")

    with pytest.raises(pytest.fail.Exception, match="CI must install helm"):
        require_helm()


def test_require_helm_skips_outside_ci_when_helm_is_missing(path_without_helm, monkeypatch) -> None:
    monkeypatch.delenv("CI", raising=False)

    with pytest.raises(pytest.skip.Exception, match="helm CLI not available"):
        require_helm()
