---
id: '0879'
title: Audience Poll Binding Runs Through the Outbox
status: Proposed
created: 2026-11-18
dependencies: 
- TASK-0849
governing_adrs:
- ADR-0001
- ADR-0011
governing_prds:
- PRD-0011
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0879: Audience Poll Binding Runs Through the Outbox

## Status
Proposed

## Summary
Follow-up of TASK-0849. Audience Studio now commits a poll and then writes its SpiceDB campaign binding. A bind failure answers 503, but the poll stays stored without a binding, so no campaign member can read it. Move the bind to the outbox relay (`services/audience_studio/src/eventSourcing/outboxRelay.ts`), so it retries until it succeeds, or give the poll a state that the read path reports.

## Open Questions
1. Does the outbox relay get a SpiceDB port, or does a second relay own the binding?
2. What does a reader see for a poll whose binding is still pending?

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
