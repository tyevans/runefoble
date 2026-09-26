---
id: 0004
title: Isolated Component Development in Storybook
status: Accepted
created: 2026-09-25
governing_prd: PRD-0013
---

# US-0004 — Isolated Component Development in Storybook

## Governing PRD
- [`PRD-0013: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)

## User Story

**As a** frontend engineer building UI widgets for Runefoble,
**I want to** build and test Lit web components in Storybook with hot reloading and configurable mock properties,
**So that** I verify edge cases (e.g. low HP states, complex condition lists, varying grid dimensions) before mounting them into the main application.

## Acceptance Criteria

1. **Standalone Storybook Studio**: `pnpm run storybook` launches Storybook dev server on port 6006.
2. **Interactive Controls**: Component arguments (`tokens`, `conditions`, `watcherStatus`) can be altered dynamically in the Storybook controls panel.
3. **Automated Static Build**: `pnpm run build-storybook` generates a zero-error static build in CI.
