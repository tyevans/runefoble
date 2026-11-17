---
id: '0631'
title: Silence Intentional Event Type Warnings and Keep Event Registry Imports Clean
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0006
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: low
source_audits:
- w1-gates-python.md
- w1-libs.md
- w3-event-wiring.md
- w2-voice-agent.md
---

# TASK-0631: Silence Intentional Event Type Warnings and Keep Event Registry Imports Clean

## Status
Complete

## Summary
Importing `runefoble_events` prints `Event class X has event_type='Y' which differs from class name` for several classes. The eventsource-py library emits this warning from `DomainEvent.__init_subclass__` (`eventsource/domain/event.py:195-200`) unless the class sets `suppress_event_type_warning`. Thirty files already use that flag, but the Mercenary Bounty contracts and others do not. Keep the wire types (they are documented and used on streams), suppress the warning only for intentional prefixed names, and add a test that importing the package logs nothing.

## Problem Statement
- Warnings are printed on import for `MercenaryBountyPostedEvent`, `MercenaryBountyClaimedEvent`, `MercenaryBountyFulfilledEvent` (`libs/runefoble_events/src/runefoble_events/contracts.py:14-60`) and others (`.audit/reports/w1-libs.md` F16, `w1-gates-python.md` F2).
- `w3-event-wiring.md` F12 counts 132 classes whose explicit `event_type` differs from the class name. Only classes without the suppress flag warn.
- The pattern is inconsistent: `voice_barge_in.py`, `turf_war.py`, and others set the flag; `contracts.py` does not.

## Documentation & Architecture Review
- `docs/reference/events-schema.md` documents the Mercenary Bounty wire types (for example `MercenaryBountyPosted`). Keep them; do not rename streams.
- ADR-0011: event registry rules. ADR-0006: stream names unchanged.
- Overlap: TASK-0487 deletes shadowed root event modules and touches the same package. Sequence after it or coordinate the merge.

## Product & User Story References
- None; platform hygiene.

## Detailed Specification & Implementation Plan
1. Decision (recorded in the task PR): keep all wire types. Add `suppress_event_type_warning: ClassVar[bool] = True` to every class whose explicit `event_type` is an intentional, documented wire type that differs from the class name. Use the same pattern as `voice_barge_in.py`.
2. Grep for explicit `event_type` assignments in `libs/runefoble_events`. Apply the flag to each that warns on import. Do not change any string value.
3. Add `tests/test_event_registry_import_clean.py`: import `runefoble_events` in a subprocess with `PYTHONWARNINGS=error` and capture the eventsource logger; assert no output.
4. Check that no event class has two `@register_event` wire types (w3 F12 `voice.py:108-109`); report, but fix only if trivial.

## Frontdoor Blackbox Test Plan
- Before fix: importing `runefoble_events` in a fresh process prints the warnings to stderr.
- After fix: the subprocess test shows empty stderr for the import; existing bounty flows still publish `runefoble.events.session` events (covered by the game-session bounty suite).

## Definition of Done
1. Import of `runefoble_events` emits no warnings.
2. No wire type string changed.
3. The registry import test passes.
4. Coordination with TASK-0487 recorded.
5. No file above 500 lines.
