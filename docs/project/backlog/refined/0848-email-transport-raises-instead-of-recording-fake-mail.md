---
id: '0848'
title: Email Transport Raises on Failure and Keeps No Fake Sent Mail
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0848: Email Transport Raises on Failure and Keeps No Fake Sent Mail

## Status
Refined

## Summary
The SMTP transport in `runefoble_platform` records mail in memory when the SMTP server is down. The default is on. The caller gets a normal return value, so a failed send looks like a success. The Mailpit client also returns `None` or `True` on failure. The fix removes the in-memory fallback from production code, makes failures raise, and moves the test recorder to `tests/helpers/`.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/email/smtp.py:36`: `fallback_in_memory: bool = True`.
- `smtp.py:78-87`: on any SMTP exception the code logs a warning and then appends the message to `self.sent_emails` after the block, so the caller sees success.
- `libs/runefoble_platform/src/runefoble_platform/email/mailpit.py:55` and `:57`: the default `True` is repeated and passed to the parent.
- `mailpit.py:66-67` (`_get`): returns `None` on any failure. `check_health` then loses the cause.
- `mailpit.py:111-112` (`delete_all_messages`): returns `True` when the purge fails.
- The only test caller is `tests/test_platform_email_modular_decomposition.py`. No service imports the client.

## Documentation & Architecture Review
- ADR-0015 Context item 4: fallbacks hide failures. Production code paths must not select in-memory adapters (as ADR-0015 (f) says for event stores).
- `docs/how-to/test-email-signups-with-mailpit.md` and `docs/reference/platform-services.md` describe Mailpit. Check them for the fallback. Fix them if they describe it.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Remove the `fallback_in_memory` parameter and the `sent_emails` recorder from `smtp.py`. Let the SMTP exception propagate. Use a typed error from `runefoble_platform` if the module has one.
2. Move the in-memory recorder to `tests/helpers/email_recorder.py` for tests that need it.
3. In `mailpit.py`, `_get` raises on transport errors and on non-200 responses. `delete_all_messages` raises instead of returning `True` after a failure.
4. Keep `check_health` as the one place that turns a failure into a status. It reports the cause text.
5. Remove the `fallback_in_memory` argument from every caller. Do not keep an alias.

## Frontdoor Blackbox Test Plan
- Start the SMTP path with a closed port. Call `send_email`. Assert it raises the typed error.
- Start Mailpit with a stub that returns 500 on purge. Call `delete_all_messages`. Assert it raises.
- Call `check_health` with Mailpit down. Assert the status is unhealthy and the message contains the cause.
- Send with a live Mailpit double. Assert the message is visible through the Mailpit HTTP API, not through a Python list.

## Definition of Done
- No production code keeps sent mail in memory.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F1)
