---
id: '0966'
title: Redis Requires a Password, and Loki and Grafana Keep Their Data
status: Proposed
created: 2026-11-19
dependencies:
- '0959'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0966: Redis Requires a Password, and Loki and Grafana Keep Their Data

## Status

Proposed

## Summary

Split from TASK-0961 (backups cover PostgreSQL only). `deployments/helm/runefoble/templates/redis.yaml:23` runs Redis with no password. Loki and Grafana have no persistent volume, so a pod restart loses logs and dashboards (`.audit/research/r1-hosting.md`). In the hosted profile, Redis requires a password from the hosted secret contract (TASK-0959), every Redis client reads it, and Loki and Grafana use persistent volumes.

## Test Plan

- `helm template` with the hosted values renders `requirepass` from a Secret and a PVC for Loki and Grafana. Chart tests in `tests/test_blackbox_helm_*.py`.
- A service connects to Redis with the password in a blackbox test.
