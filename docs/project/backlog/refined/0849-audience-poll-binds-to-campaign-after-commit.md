---
id: '0849'
title: Audience Poll Binds to Its Campaign Only After the Poll Event Commits
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: audience_studio
target_release: 0.9.0
---
# TASK-0849: Audience Poll Binds to Its Campaign Only After the Poll Event Commits

## Status
Refined

## Summary
`PollEngine` writes the SpiceDB campaign binding before it commits the `poll.start` event. If the commit fails, the binding stays for a poll that does not exist. This is a dual write with no compensation. The fix commits the event first and binds the poll after the commit, through the outbox path, or it removes the binding when the commit fails.

## Problem Statement
- `services/audience_studio/src/pollEngine.ts:102`: `await this.access.bindPollToCampaign(id, params.campaignId);` runs first.
- `pollEngine.ts:103`: `await this.mutex.run([pollStreamId(id)], () => this.repo.commit([poll]));` runs second.
- If line 103 fails, the tuple from line 102 remains. The poll never exists.
- `services/audience_studio/src/access/audienceAccess.ts:85` writes the binding.

## Documentation & Architecture Review
- ADR-0011: state changes go through the event store. The SpiceDB tuple is a side effect and follows the commit.
- ADR-0015 Context item 4: a failed dependency must not look like a working one.
- `services/audience_studio/src/eventSourcing/outboxRelay.ts` already implements the outbox pattern. Check it before you choose the design.
- TASK-0724 (refined) changes the production adapter selection in the same service. Coordinate the edits.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Preferred design: commit the poll first. Bind the poll to its campaign from the outbox relay on the `poll_started` event. The relay retries until the binding succeeds.
2. If the relay cannot run in this slice, commit first and bind after the commit. If the bind fails, return 503. Do not leave a poll without a binding and do not keep a tuple without a poll.
3. Do not add a fallback that skips the binding check.
4. Add a unit test for the engine order. Add the frontdoor test below.

## Frontdoor Blackbox Test Plan
- Make the event store fail on append (the existing store double). Send `POST /polls` with a valid campaign. Assert a 5xx response.
- Read the id of the attempted poll through the public route. Assert 404, not 403.
- Successful create: assert the poll is visible to a campaign member after the relay runs, through the public `GET`.

## Definition of Done
- The commit happens before any SpiceDB write for the poll, or the write is removed on failure.
- `npm test` (audience_studio) and the Python blackbox wrapper pass. `make lint` and `make health-check` pass.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F6)
