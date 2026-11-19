---
id: '0851'
title: Event Decoder Fails Loud on Malformed or Invalid Payloads
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0851: Event Decoder Fails Loud on Malformed or Invalid Payloads

## Status
Refined

## Summary
`deserialize_event` returns different kinds of value for bad input. A non-JSON string comes back as a string. A non-JSON payload becomes `{"raw": ...}`. A registered event that fails validation logs a warning and comes back as an untyped dict. Consumers cannot tell a typed event from raw data. The fix raises a typed `EventDecodeError` for bad input and returns an explicit `UnknownEvent` value for unregistered types.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/event_deserializer.py:30-35`: a string that is not JSON is returned as the raw string.
- `event_deserializer.py:47`: a payload that is not JSON becomes `{"raw": raw_payload}`.
- `event_deserializer.py:65`: a registered event that fails `model_validate` logs a warning and returns the untyped dict.
- Callers: `libs/runefoble_platform/src/runefoble_platform/consumer_group.py:84` and `:125`.

## Documentation & Architecture Review
- ADR-0011: consumers read typed domain events.
- `docs/reference/redis-streams-event-bus.md` and `docs/reference/events-schema.md`: check the decode rules and update them.
- TASK-0718 covers telemetry only. It does not touch this module.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `EventDecodeError` in `runefoble_platform`. Raise it for an undecodable payload and for a registered event type that fails validation.
2. For an unregistered event type, return an `UnknownEvent` value object that holds the type name and the raw fields. Do not return a bare dict.
3. Update `consumer_group.py` to catch `EventDecodeError`. Record the message as failed, do not call any handler, and advance the stream position as the existing failure path does.
4. Update every test that expects a dict or a raw string.

## Frontdoor Blackbox Test Plan
- Publish a registered event with a missing required field through a Redis test double. Assert no handler runs. Assert the failure is recorded (consumer status or dead-letter stream, whichever the consumer already uses).
- Publish an unregistered event type. Assert the consumer receives an `UnknownEvent` and continues.
- Publish a non-JSON payload. Assert the same failure record as the first case.

## Definition of Done
- `deserialize_event` never returns raw input for a decode failure.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F3)
