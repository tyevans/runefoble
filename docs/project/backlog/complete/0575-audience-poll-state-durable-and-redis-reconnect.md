---
id: '0575'
title: Audience Studio Poll and Proposal State Durable, With Redis Publish Recovery
status: Complete
created: 2026-11-17
dependencies:
- TASK-0560
governing_adrs:
- ADR-0011
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0011
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0575: Audience Studio Poll and Proposal State Durable, With Redis Publish Recovery

## Status
Complete

## Summary
Audience Studio keeps polls, votes, open timers, and pending proposals in TypeScript `Map`s. Its Redis client sets `retryStrategy: () => null` and swallows `xadd` errors. A restart drops every open poll and pending DM approval, and a failed first connection disables publishing for the life of the process. This task makes poll and proposal state event-sourced, rebuilt on start, and makes publish failures visible.

## Problem Statement
- `services/audience_studio/src/pollEngine.ts:34-36` (`polls`, `votersByPoll`, `timers`) and `src/approvalQueue.ts:232` (`proposals`) are in-memory `Map`s (w2-audience-studio F4).
- `src/redis.ts:59-78` only calls `XADD`. Nothing reads the stream back and no consumer group exists.
- `src/redis.ts:24-28` sets `retryStrategy: () => null`. If the first connect fails, `isConnected` stays `false` for the life of the process (F6).
- `src/redis.ts:59-78` swallows `xadd` errors and returns a memory id, so event loss is silent (F6).
- AGENTS.md Hard Invariant 2 applies: poll and proposal changes must flow through an event-sourced aggregate. The TypeScript service needs its own aggregate module, consistent with the Python event definitions in `libs/runefoble_events/src/runefoble_events/audience.py`.

## Documentation & Architecture Review
- `docs/how-to/orchestrate-audience-chaos-polls.md` describes polls and approval. Verify it. Lines 86-88 say the chaos effect is applied to gameplay. That is false until TASK-0441 (refined) lands. Correct the doc with this task.
- TASK-0441 covers the consumer in game session and the watcher. This task does not.
- The TypeScript event store choice must follow TASK-0560 (Postgres in deployment, memory only in tests).

## Product & User Story References
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)

## Detailed Specification & Implementation Plan
1. Create `PollAggregate` and `ProposalAggregate` in `services/audience_studio/src/aggregates/` with commands `start`, `vote`, `close`, `propose`, `approve`, `reject`. Each emits an existing event class from `audience.py` (verify the names first).
2. Repository: load by id, save events, publish through the Redis client. Rebuild open polls and timers on start-up from stored deadlines.
3. Delete the `polls`, `votersByPoll`, `timers`, and `proposals` maps as sources of truth. Keep timer handles only.
4. `redis.ts`: use a bounded retry with backoff. A publish failure rejects the command (HTTP 503 or WebSocket error frame). Add `/readyz` that fails while the stream is unavailable.
5. Log publish failures at error level with stream and event type.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** create a poll through the public route, restart the service, then read the poll. Before: 404. After: the poll is open with its votes.
- **Fail before, pass after:** a poll with a 2-second window closes after a restart and emits `AudiencePollCompleted` on the stream.
- **Fail before, pass after:** start the service before Redis is reachable, then start Redis. Before: publish never recovers. After: `/readyz` becomes 200 and a vote is published.
- Public routes and WebSocket only.

## Definition of Done
1. No in-memory poll or proposal map is a source of truth (grep).
2. Three tests above pass. `pnpm run build` and the TypeScript tests pass.
3. How-to corrected. Events-schema audience section matches the code.
4. `CHANGELOG.md` entry. Files under 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-audience-studio.md`
