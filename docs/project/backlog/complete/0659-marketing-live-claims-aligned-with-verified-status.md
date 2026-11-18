---
id: '0659'
title: Platform Showcase Marketing Page Labels Only Verified Capabilities as Live
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0659: Platform Showcase Marketing Page Labels Only Verified Capabilities as Live

## Status
Complete

## Summary
`docs/marketing.md` describes several capabilities as live that the audit found canned, unwired, or not persisted. Its roadmap labels also disagree with `docs/project/backlog/ROADMAP.md`. AGENTS.md DoD 11 requires the showcase to keep live capabilities and roadmap status aligned with the platform. Correct each claim to one of three verdicts: Supported, Partly supported (with the limit stated), or Not yet live (with the blocking task). Sync the roadmap status from ROADMAP.md and PRIORITY.md.

## Problem Statement
- M-1 (high): lines 102-135 label Milestone 2 "(Current)", Milestone 3 "(Next)", and Milestone 4 "(Future)". `docs/project/backlog/ROADMAP.md` marks Milestones 1 to 9 and 11 Complete, with Milestone 10 Active. `PRIORITY.md:55` marks TASK-0074 Complete, but marketing line 113 leaves the same item unchecked.
- M-2 (high, lines 60-71, 76-77): spoken commands and Watcher parsing are not supported as live. The speak route is canned (`tabletop.py:183-193`). No UI calls the transcribe or intent routes.
- M-3 (high, lines 77-78): the autonomous DM is not live. The real LLM path is not wired. Domain state is in process memory, not aggregates.
- M-4 (high, lines 42, 79-80): AI stand-ins are not live. Activation is never persisted or triggered. Only one penalty is applied.
- M-5 (medium, lines 70-74): the board is partly supported. The gateway serves canned board data (`gateway/api/src/gateway_api/routers/tabletop.py:179-180`), and board state is not durable.
- M-6 (high, lines 87-89): "zero-trust" and "enforces" authorization claims are not supported. Role assignment has no authentication. The dev identity bypass is on by default.
- M-7 (high, line 146): "event sourcing on PostgreSQL" and "time-travel debugging" are not supported as deployed. The game session uses `InMemoryEventStore`.
- M-8 (high, line 151): FastMCP dice, board, and lore tools are not supported. The static tools return canned data.
- M-9 (high, lines 152, 214-215): "single-command cloud deployment" is not supported. Only the frontend has a Dockerfile. Local Kind creation is supported.
- M-10 (medium, line 90): `/ui/manifest` is partly supported. It is per-service only.
- M-11 (medium, line 91): "WCAG 2.1 AA" is not verified. No contrast test exists.
- M-12 (medium, line 92): OpenTelemetry and OpenPanel end to end are partly supported. The default is off.
- M-13 and M-14 (low): latency claims and voice DSP claims are not verified.

## Documentation & Architecture Review
- `docs/project/backlog/ROADMAP.md` is the status source for milestones. `PRIORITY.md` is the source for task status. Both are read-only for this task.
- Each claim links to the evidence it rests on (the blocking task id or the audit report). The showcase does not invent new status.
- DoD 9 and 11: the orchestrator syncs the roadmap at integration. This task changes the marketing file only.

## Product & User Story References
Marketing and platform communication. The governing PRDs are the ones the claims cite; no single PRD applies.

## Detailed Specification & Implementation Plan
1. Create a verdict legend at the top of the page: Live, Partly live (limit stated), Not yet live (blocked by task id).
2. Re-label each M-item per the verdicts above. Keep the wording short. Remove "zero-trust", "time-travel debugging", "single-command cloud", and "live" from the sections that are not live.
3. Milestone block: take status from `ROADMAP.md`. Tick only items whose backlog task is in `complete/`.
4. Remove all unverified latency numbers (M-13) or link to a measurement.
5. Add a line under each limited section naming the blocking task id (TASK-0600 to TASK-0602 for voice, TASK-0641 for the feed, and so on).
6. Keep the file under 500 lines.

## Frontdoor Blackbox Test Plan
- A script (`scripts/check_marketing_status.py` (removed), run with `uv run`) reads `ROADMAP.md` and `PRIORITY.md` and fails when a milestone or item is ticked on the marketing page but not Complete in the backlog.
- A second check fails when the page contains "zero-trust", "time-travel", or "single-command cloud" without a link to a verdict.
- Before the edit the script FAILS on lines 102-135 and 60-80. After the edit it PASSES.

## Definition of Done
1. Every claim in `docs/marketing.md` has a verdict and, where limited, a blocking task id.
2. The milestone status matches `ROADMAP.md`.
3. The status check script runs in `make health-check` or in `spec-ops health` (TASK-0668 decides the target).
4. No claim in the page cites a canned, fixture, or in-memory path as live.

## Audit Provenance

- Severity: high
- Source audits: `w3-docs-integrity.md`
