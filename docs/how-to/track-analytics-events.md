# How-To: Track Privacy-Preserving Analytics with OpenPanel

## Overview
Runefoble integrates with self-hosted OpenPanel (`openpanel/openpanel`) to record operational and gameplay metrics (such as session counts, turn durations, and absentee stand-in activations) without tracking personally identifiable information (PII) or recording audio transcripts.

## Core Rules for Event Tracking
1. **Never log raw audio or transcripts**: Audio data belongs strictly in the ephemeral voice pipeline or user-consented session recordings.
2. **Anonymize user identifiers**: Profile IDs must be hashed or pseudonymized before reporting to OpenPanel.
3. **Asynchronous dispatch**: Analytics calls must never block user interactions, audio streaming, or game turn adjudication.

---

## Step 1: Use `OpenPanelClient` in Platform Code

The platform client provides non-blocking event recording:

```python
from runefoble_platform.analytics import OpenPanelClient
from runefoble_platform.config import PlatformSettings

settings = PlatformSettings()
client = OpenPanelClient(
    endpoint=settings.openpanel_endpoint,
    client_id=settings.openpanel_client_id,
)

# Track a high-level game event
await client.track(
    event_name="session_started",
    properties={
        "campaign_type": "fantasy_5e",
        "num_players": 4,
        "is_ai_dm": True,
    },
    profile_id="anon_user_sha256",
)
```

In offline development or unit tests, `OpenPanelClient` queues events in memory and avoids remote network calls.

---

## Step 2: Stream Domain Events to OpenPanel

Rather than scattering manual analytics calls across domain services, use an asynchronous Redis Streams consumer group worker:

```python
from eventsource.domain.event import DomainEvent
from runefoble_events.session import GameSessionStarted, PlayerJoinedSession
from runefoble_platform.analytics import OpenPanelClient

async def handle_domain_event_analytics(event: DomainEvent, client: OpenPanelClient):
    if isinstance(event, GameSessionStarted):
        await client.track(
            event_name="game_session_started",
            properties={"session_id": event.session_id},
        )
    elif isinstance(event, PlayerJoinedSession):
        await client.track(
            event_name="player_joined",
            properties={
                "session_id": event.session_id,
                "role": event.role,
            },
        )
```

---

## Step 3: Frontend Event Tracking

Frontend Lit components emit analytics via the gateway proxy route (`/analytics/event`):

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

Open the OpenPanel dashboard at `http://localhost:3000` to inspect live events, funnels, and retention charts.
