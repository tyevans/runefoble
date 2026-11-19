---
id: '0869'
title: Helm Chart Tests Share One Renderer and Fail in CI When Helm Is Missing
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0010
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0869: Helm Chart Tests Share One Renderer and Fail in CI When Helm Is Missing

## Status
Refined.

## Summary
Thirteen test files run `helm template` through their own helper. Most of them skip when helm is missing. A CI host without helm then passes these chart tests with no assertion. DoD item 8 requires `helm template` to pass. One helper and one `require_helm()` gate replace the copies, and CI fails when helm is absent.

## Problem Statement
- Thirteen files call `helm template` through their own helper. Examples: `tests/test_blackbox_zitadel_issuer_config.py:24`, `tests/test_blackbox_inference_worker_chart.py:23`, `tests/test_blackbox_helm_ingress_ws.py:20`, `tests/test_blackbox_helm_secrets.py:27-42`, `tests/test_blackbox_deployability_images.py:221`, `tests/test_blackbox_redis_url_env_name.py:59`.
- `tests/test_blackbox_helm_secrets.py:27-29`: `_require_helm()` skips when `shutil.which("helm")` is empty. The same skip exists in the other files. There are 13 skip sites.
- `tests/test_blackbox_service_credential.py:148` (`_run_import`) and `tests/test_blackbox_service_identity.py:180` (`_run_worker_import`) build the same child-process environment filter.
- `.github/workflows/ci.yml:90-105` installs helm only in the `helm-lint` job. Confirm whether the Python test job has helm before you merge.

## Documentation & Architecture Review
- ADR-0005 (Helm and Kind are the deployment path). ADR-0010 (CI pipeline).
- AGENTS.md DoD item 8: `helm lint` and `helm template` must pass.
- `docs/reference/cli-interfaces.md` lists the test gates. Update it if it names the skip behaviour.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `tests/helpers/helm.py` with `render_chart(*extra_args) -> list[dict]`, which runs `helm template runefoble deployments/helm/runefoble` and parses the YAML documents.
2. Add `require_helm()` to the same module. If `helm` is missing and the `CI` environment variable is set, it fails the test. Otherwise it skips, for a developer machine.
3. Replace the thirteen render helpers and skip sites with these two functions.
4. Add `run_python_child(code, env_overrides, cwd)` to `tests/helpers/process.py`. Use it in `test_blackbox_service_credential.py` and `test_blackbox_service_identity.py`. The environment filter stays in one place.
5. In `.github/workflows/ci.yml`, add `azure/setup-helm@v4` to the job that runs pytest, if that job lacks helm.

## Frontdoor Blackbox Test Plan
- The thirteen chart suites pass unchanged on a host with helm.
- Helper test: with `CI=true` and helm removed from `PATH`, `require_helm()` fails. Without `CI`, it skips.
- The two child-process suites pass unchanged.

## Definition of Done
- One render helper and one skip gate in `tests/helpers/helm.py`. No other `helm template` call in `tests/`.
- CI host has helm for the Python test job.
- `uv run pytest` and `make health-check` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: high
- Source audits: `tests`
