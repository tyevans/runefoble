# How-To: Track Privacy-Preserving Analytics with OpenPanel

## Overview
Runefoble integrates with self-hosted OpenPanel (`openpanel/openpanel`) to record operational and gameplay metrics (such as session starts, dice rolls, turn durations, and absentee stand-in activations) without tracking personally identifiable information (PII) or recording audio transcripts.

## Core Rules for Event Tracking
1. **Never log raw audio or transcripts**: Audio data belongs strictly in the ephemeral voice pipeline. Property keys matching `audio`, `transcript`, `speech`, or `dialogue` are stripped automatically.
2. **Anonymize user identifiers**: Profile IDs are automatically hashed using salted SHA-256 before reporting to OpenPanel.
3. **Asynchronous dispatch**: Analytics calls never block user interactions, audio streaming, or game turn adjudication.
4. **Decoupled domain pipeline**: Domain services publish domain events to Redis Streams; the background `AnalyticsEventWorker` maps them to privacy-preserving telemetry metrics.

---

## Modular Subpackage Architecture

To comply with Hard Invariant 6 (File length limit < 500 lines) and support clean separation of concerns, the analytics package is structured into single-responsibility submodules:

- `runefoble_platform.analytics.privacy`: PII scrubbing (`sanitize_properties`), salted SHA-256 ID anonymization (`anonymize_profile_id`), and forbidden property keys (`FORBIDDEN_PROPERTY_KEYS`).
- `runefoble_platform.analytics.client`: Asynchronous OpenPanel HTTP client (`OpenPanelClient`) with event buffering and mock mode.
- `runefoble_platform.analytics.worker`: Background Redis Streams consumer worker (`AnalyticsEventWorker`) translating CloudEvents to OpenPanel metrics.
- `runefoble_platform.analytics`: Unified re-export facade providing 100% backward compatibility for top-level imports.

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

## Step 2: Stream Domain Events with `AnalyticsEventWorker`

Rather than scattering manual analytics calls across domain aggregates, deploy the background `AnalyticsEventWorker` consuming domain events from Redis Streams (`runefoble.events.session`, `runefoble.events.watcher`):

```python
from runefoble_platform.analytics import AnalyticsEventWorker, OpenPanelClient
from runefoble_platform.consumer_group import RedisConsumerGroup

consumer_group = RedisConsumerGroup(redis_url="redis://localhost:6379/0")
client = OpenPanelClient()

worker = AnalyticsEventWorker(
    client=client,
    consumer_group=consumer_group,
    streams=["runefoble.events.session", "runefoble.events.watcher"],
    group_name="runefoble_analytics_workers",
    consumer_name="analytics_worker_1",
)

# Start background async consumer loop
await worker.start()

# When shutting down
await worker.stop()
```

### Event Mapping Taxonomy

| Domain Event | OpenPanel Metric | Tracked Properties (Anonymized) |
|---|---|---|
| `SessionStarted` / `GameSessionStarted` | `session.started` | `session_id`, `started_at_turn` |
| `SessionCreated` | `session.created` | `session_id`, `dm_id` |
| `SessionEnded` | `session.ended` | `session_id`, `summary` |
| `DiceRolled` / `DiceRollEvent` | `dice.rolled` | `session_id`, `formula`, `total`, `is_crit`, `is_fumble`, `roll_type` |
| `StandInActionDecided` / `StandInTurnExecuted` | `stand_in.turn_taken` | `character_name`, `action_type`, `penalties_applied` (no dialogue/transcripts) |
| `AbsencePenaltyApplied` / `PlayerAbsenteePenalized` | `stand_in.penalty_applied` | `penalty_type`, `imposed_by` |
| `PlayerJoinedSession` | `player.joined` | `session_id`, `character_class` |
| `PlayerLeftSession` | `player.left` | `session_id`, `reason` |

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
