---
id: '0970'
title: The Helm Values File Is Split Below 500 Lines
status: Proposed
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0005
governing_prds: []
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0970: The Helm Values File Is Split Below 500 Lines

## Status

Proposed

## Summary

`deployments/helm/runefoble/values.yaml` is 521 lines after the Release One chart work (Hard Invariant 6). Workers put new keys in `values.hosted.example.yaml` to avoid growing it, and some keys now rely on code defaults only (`.audit/work/0948.md`, Discovered 2). Split the file by concern (for example platform services, app services, observability) so that each file is under 500 lines, keep the local render byte-identical, and put each documented key in exactly one values file. A chart test compares the local render before and after.
