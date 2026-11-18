# How-To: Track Privacy-Preserving Analytics with OpenPanel

## Overview
Runefoble integrates with self-hosted OpenPanel (`openpanel/openpanel`) to record operational and gameplay metrics (such as session starts, dice rolls, turn durations, and absentee stand-in activations) without tracking personally identifiable information (PII) or recording audio transcripts.

## Core Rules for Event Tracking
1. **Never log raw audio or transcripts**: Audio data belongs strictly in the ephemeral voice pipeline. Property keys matching `audio`, `transcript`, `speech`, or `dialogue` are stripped automatically.
2. **Anonymize user identifiers**: Profile IDs are automatically hashed using salted SHA-256 before reporting to OpenPanel.
3. **Asynchronous dispatch**: Analytics calls never block user interactions, audio streaming, or game turn adjudication.
4. **Explicit reporting**: Domain services publish domain events to Redis Streams. No worker forwards them to OpenPanel. A service that reports a metric calls `OpenPanelClient` itself.

---

## Modular Subpackage Architecture

To comply with Hard Invariant 6 (File length limit < 500 lines) and support clean separation of concerns, the analytics package is structured into single-responsibility submodules:

- `runefoble_platform.analytics.privacy`: PII scrubbing (`sanitize_properties`), salted SHA-256 ID anonymization (`anonymize_profile_id`), and forbidden property keys (`FORBIDDEN_PROPERTY_KEYS`).
- `runefoble_platform.analytics.client`: Asynchronous OpenPanel HTTP client (`OpenPanelClient`) with event buffering and mock mode.
- `runefoble_platform.analytics`: Defect (DoR 9): unified re-export facade for top-level imports. Removal: TASK-0485.

---

## Step 1: Use `OpenPanelClient` in Platform Code

The platform client provides non-blocking event recording and automated PII sanitization:

```python
from runefoble_platform.analytics import OpenPanelClient
from runefoble_platform.config import PlatformSettings

settings = PlatformSettings()
client = OpenPanelClient(
    endpoint=settings.openpanel_endpoint,
    client_id=settings.openpanel_client_id,
    salt="runefoble_privacy_salt",
    mock_mode=False,
)

# Track a high-level game event
await client.track(
    event_name="session.started",
    properties={
        "campaign_type": "fantasy_5e",
        "num_players": 4,
        "is_ai_dm": True,
    },
    profile_id="user_player_123",  # Automatically hashed via SHA-256 with salt
)
```

In offline development or unit tests, pass `mock_mode=True` to buffer events in `client.recorded_events` without remote network requests.

---

## Step 2: Report Domain Events Explicitly

No background worker forwards Redis Streams events to OpenPanel. The platform `AnalyticsEventWorker` was removed because no service started it. To report a metric from a domain event, call `OpenPanelClient` from the handler that owns the event. Keep the handler on the owning service's consumer, as described in [Run Supervised Redis Stream Consumers](run-supervised-redis-stream-consumers.md).

The table below is the planned mapping for a future forwarder. It is not implemented.

### Planned Event Mapping Taxonomy (not implemented)

| Domain Event | OpenPanel Metric | Tracked Properties (Anonymized) |
|---|---|---|
| `runefoble.events.session.started` | `session.started` | `session_id`, `started_at_turn` |
| `runefoble.events.session.created` | `session.created` | `session_id`, `dm_id` |
| `runefoble.events.session.ended` | `session.ended` | `session_id`, `summary` |
| `DiceRolled` | `dice.rolled` | `session_id`, `formula`, `total`, `is_crit`, `is_fumble`, `roll_type` |
| `runefoble.events.watcher.stand_in_action_decided` | `stand_in.turn_taken` | `character_name`, `action_type`, `penalties_applied` (no dialogue/transcripts) |
| `runefoble.events.character.absence_penalty_applied` | `stand_in.penalty_applied` | `penalty_type`, `imposed_by` |
| `runefoble.events.session.player_joined_session` | `player.joined` | `session_id`, `character_class` |
| `runefoble.events.session.player_left_session` | `player.left` | `session_id`, `reason` |

---

## Step 3: Frontend Event Tracking

Frontend Lit components emit client-side UI telemetry via the Traefik ingress route (`/analytics/event`):

```typescript
export async function trackEvent(name: string, props: Record<string, unknown> = {}) {
  try {
    await fetch('/analytics/event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: name,
        properties: props,
      }),
    });
  } catch (err) {
    // Fail silently in frontend to prevent UX degradation
    console.debug('Analytics dispatch failed:', err);
  }
}
```

---

## Step 4: Verify in OpenPanel Dashboard

In local Kind development, navigate to `http://runefoble.local/analytics` (or port-forward `kubectl port-forward svc/openpanel 3000:3000`) to inspect real-time events, funnels, and retention charts.

---

## 5. Modular Blackbox Test Organization & Architecture

The OpenPanel analytics test suite is partitioned into two focused blackbox test modules strictly adhering to Hard Invariant 6 (< 500 lines per file, strictly < 180 lines) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
- `tests/test_blackbox_analytics_client.py`: Verifies salted SHA-256 profile anonymization, recursive PII property scrubbing (audio bytes, speech transcripts, secret credentials), HTTP transport dispatch via `OpenPanelClient`, and fast failure modes.
- `tests/test_blackbox_stream_consumers.py`: Verifies the supervised stream consumers of Campaign Analytics and Soundscape. The OpenPanel forwarder has no test because it does not exist.

