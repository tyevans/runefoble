---
id: '0798'
title: Kind Stack Deploys From a Clean Cluster With One Command
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: deployments
target_release: 0.9.0
---

# TASK-0798: Kind Stack Deploys From a Clean Cluster With One Command

## Status
Complete

## Summary
`make cluster-up images helm-deploy` does not bring up a working stack. The Helm post-install hook times out. Zitadel panics, the bootstrap Job waits for a secret no step creates, every Runefoble service waits for the client secret that Job writes, and two upstream image tags do not exist. The frontend image build also failed (fixed in commit on main: libs/runefoble_ui added to the build context).

## Problem Statement
- `deployments/helm/runefoble/templates/zitadel.yaml`: `start-from-init` runs without `--masterkeyFromEnv`, so Zitadel ignores `ZITADEL_MASTERKEY` and panics with "No master key provided".
- `zitadel-bootstrap` Job needs Secret `zitadel-admin` (the machine user PAT). Zitadel prints the PAT to its log. No step stores it.
- Every service pod: `secret "runefoble-zitadel-client" not found` (the Job writes it).
- `values.yaml:140` `minio/minio:RELEASE.2024-01-01T00-00-00Z` does not exist. `values.yaml:199` `openpanel/openpanel:latest` does not exist.
- `values.yaml:193` `authzed/zed:latest` is unpinned.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0005, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Pass `--masterkeyFromEnv` to Zitadel.
2. Make the PAT reach the bootstrap Job with no manual step: for example `ZITADEL_FIRSTINSTANCE_PATPATH` on a volume, and a step in the Zitadel pod or the Job that stores it in the `zitadel-admin` Secret. Keep RBAC to the named Secrets.
3. Pin real, existing tags for Silo (MinIO), OpenPanel and zed. Verify each with `docker manifest inspect` or `docker pull`.
4. Services must not crash-loop while the bootstrap runs: they wait for the Secret (the current behaviour) and start when it appears.
5. Update `docs/tutorials/01-local-development-setup.md` with the real expected results and timing.

## Frontdoor Blackbox Test Plan
- From a released state (`helm uninstall runefoble`, release PVCs removed), `make helm-deploy` exits 0 and every pod in the release is Running or Completed within the hook timeout.
- `curl -s localhost/healthz` through Traefik answers 200 from gateway-api, and its downstream probes report each service.
- The Zitadel discovery document is served at the configured issuer.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: Orchestrator Kind deploy for TASK-0525, 2026-11-18 (`.audit/work/kind-helm.log`)
