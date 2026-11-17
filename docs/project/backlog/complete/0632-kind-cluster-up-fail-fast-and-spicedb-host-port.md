---
id: '0632'
title: Fail cluster-up on Ingress Install Errors and Fix the SpiceDB Host Port Mapping
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
governing_prds: []
governing_stories:
- US-0010
target_release: 0.9.0
severity: low
source_audits:
- w1-gates-infra.md
---

# TASK-0632: Fail cluster-up on Ingress Install Errors and Fix the SpiceDB Host Port Mapping

## Status
Complete

## Summary
`make cluster-up` hides Traefik installation failures with `2>/dev/null || true` and then prints "Cluster is ready!" regardless. The Kind config also maps host port 50051 to the node while the SpiceDB Service is ClusterIP, so nothing listens on the host. Make cluster-up fail when ingress fails, and either expose SpiceDB deliberately or drop the mapping.

## Problem Statement
- `Makefile` cluster-up lines (about 73-77) end the Traefik commands with `2>/dev/null || true` and print success (`w1-gates-infra.md` F9).
- `deployments/kind/cluster-config.yaml` maps containerPort 50051 to hostPort 50051. `deployments/helm/runefoble/templates/spicedb.yaml` sets `type: {{ .Values.spicedb.serviceType | default "ClusterIP" }}`, and values set no `serviceType` (`w1-gates-infra.md` F8).

## Documentation & Architecture Review
- ADR-0005: Kind plus Traefik on host ports 80 and 443 is the local ingress contract.
- `docs/tutorials/01-local-development-setup.md` describes cluster-up; update it if behaviour changes.

## Product & User Story References
- US-0010 (developer local infrastructure).

## Detailed Specification & Implementation Plan
1. Remove `2>/dev/null` and `|| true` from the Traefik apply, repo add, and helm upgrade steps, except the `helm repo add` idempotence case, which should check for an existing repo first.
2. Choose one for SpiceDB: (a) set `spicedb.serviceType: NodePort` with a fixed `nodePort: 30051` mapped from host 50051, or (b) remove the 50051 mapping. Record the choice. Default recommendation: (b), since no backlog task requires host gRPC access.
3. Keep the success message only after `kubectl -n kube-system rollout status deploy/traefik` succeeds.

## Frontdoor Blackbox Test Plan
- Before fix: with Traefik install forced to fail (for example an unreachable chart repo), `make cluster-up` exits 0 and prints "Cluster is ready!".
- After fix: the same condition exits non-zero and prints no ready message. With the chosen SpiceDB option, `grpcurl` or a TCP connect to the host port behaves as documented.

## Definition of Done
1. cluster-up exits non-zero on ingress failure.
2. SpiceDB host mapping matches the docs.
3. Tutorial updated.
4. Manual verification on a Kind cluster recorded in the PR.
5. No file above 500 lines.
