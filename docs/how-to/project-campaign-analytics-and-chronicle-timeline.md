# How-To: Project Campaign Analytics & Chronicle Timeline

This guide explains how to project combat telemetry, query tactical damage heatmaps, evaluate encounter MVP statistics, and retrieve campaign milestone chronicles using the `services/campaign_analytics` bounded context microservice (ADR-0001, ADR-0003, ADR-0005, ADR-0006, ADR-0011, ADR-0013).

---

## 1. Architecture & Telemetry Pipeline

The Campaign Analytics microservice operates as a CQRS projection engine and chronicle archive:

1. **Redis Streams Ingestion**: Dedicated worker (`campaign_analytics_worker`) listens to event streams:
   - `runefoble.events.session`: Encounter lifecycle (`CombatRoundAdvanced`, `SessionEnded`).
   - `runefoble.events.board`: Spatial movements (`TokenMoved`).
   - `runefoble.events.character`: Damage and healing deltas (`CharacterHealthChanged`).
   - `runefoble.events.watcher`: Tabletop actions (`DiceRolled`).
2. **PostgreSQL Analytical Persistence**: Telemetry points, performance records, and chronicle milestones are stored in relational tables (`campaign_spatial_telemetry`, `combat_performance_records`, `campaign_timeline_milestones`) with SQLite/in-memory fallback for local testing.
3. **Event-Sourced Milestones**: Domain milestones and MVP snapshots are managed by `CampaignChronicleAggregate` (`eventsource-py`) emitting `ChronicleMilestoneRecorded`, `CombatTelemetrySnapshotCreated`, and `EncounterMvpAwarded`.

```
Redis Streams ───► CampaignAnalyticsWorker ───► AnalyticsEventDispatcher ───► PostgreSQL Storage
                                                                                    │
                                                                                    ▼
Zanzibar Auth ───► FastAPI APIRouters ◄──────────────────────────────────────── Analytics Queries
                   ├─ /heatmap
                   ├─ /mvp
                   └─ /timeline
```

---

## 2. SpiceDB Zanzibar Object Authorization

Access to campaign analytics and chronicle records is protected by SpiceDB Zanzibar object permissions (`libs/runefoble_auth/schema/runefoble.zed`):

- **Permission**: Callers must possess the `view` permission on the target campaign (`campaign:<campaign_id>`).
- **Roles**: Users holding `owner`, `dungeon_master`, `player`, or `spectator` relations automatically inherit `view` permission.
- Unauthorized callers receive HTTP `403 Forbidden`.

When querying endpoints, provide the authenticated user ID via the `X-User-Id` header (or Zitadel JWT bearer token):

```http
GET /api/v1/analytics/campaigns/c5f8742d-cfca-4fbc-8911-37d363b9f4a1/heatmap
X-User-Id: sarah_player
```

---

## 3. Querying Spatial Damage Heatmaps

The heatmap endpoint aggregates token coordinates, hit frequencies, and damage densities across combat rounds:

```http
GET /api/v1/analytics/campaigns/{campaign_id}/heatmap?cell_size=5&encounter_id={optional_encounter_id}
```

### Example Response
```json
{
  "campaign_id": "c5f8742d-cfca-4fbc-8911-37d363b9f4a1",
  "cell_size": 5,
  "cells": [
    {
      "x": 10,
      "y": 15,
      "hit_count": 3,
      "damage_total": 45,
      "lethality_score": 0.75
    },
    {
      "x": 15,
      "y": 15,
      "hit_count": 1,
      "damage_total": 12,
      "lethality_score": 0.20
    }
  ],
  "total_events": 4
}
```

---

## 4. Retrieving Party MVP Statistics

The MVP endpoint evaluates combat telemetry per encounter or across the entire campaign, calculating awards based on damage dealt, healing performed, and critical rolls:

```http
GET /api/v1/analytics/campaigns/{campaign_id}/mvp?encounter_id={optional_encounter_id}
```

### Example Response
```json
{
  "campaign_id": "c5f8742d-cfca-4fbc-8911-37d363b9f4a1",
  "encounter_id": "e0a29481-c30c-4bc4-b778-958b4b1a4387",
  "mvp_awards": [
    {
      "combatant_id": "char-valeros",
      "combatant_name": "Valeros",
      "category": "damage_dealer",
      "score": 68.0,
      "rationale": "Dealt highest total damage (68 dmg)"
    },
    {
      "combatant_id": "char-kyra",
      "combatant_name": "Kyra",
      "category": "lifesaver",
      "score": 34.0,
      "rationale": "Provided critical party healing (34 HP restored)"
    }
  ],
  "combatants": [
    {
      "combatant_id": "char-valeros",
      "combatant_name": "Valeros",
      "damage_dealt": 68,
      "damage_taken": 22,
      "healing_given": 0,
      "critical_hits": 2,
      "rounds_active": 3
    }
  ]
}
```

---

## 5. Navigating Chronicle Milestone Timelines

The chronicle timeline presents chronological session recaps, boss encounters, and story milestones:

```http
GET /api/v1/analytics/campaigns/{campaign_id}/timeline
```

### Example Response
```json
{
  "campaign_id": "c5f8742d-cfca-4fbc-8911-37d363b9f4a1",
  "milestones": [
    {
      "milestone_id": "m1",
      "session_id": "sess-01",
      "title": "Session 1 Concluded",
      "description": "Party defeated the Goblin Ambush and recovered the Sunstone",
      "milestone_type": "session_recap",
      "timestamp": "2026-09-26T14:00:00Z",
      "tags": ["session", "recap"]
    },
    {
      "milestone_id": "m2",
      "session_id": "sess-02",
      "title": "Defeat of the Red Dragon",
      "description": "Party vanquished Ignis the Terrible at Dragon's Peak",
      "milestone_type": "boss_defeat",
      "timestamp": "2026-09-26T15:30:00Z",
      "tags": ["boss", "combat", "victory"]
    }
  ],
  "total_milestones": 2
}
```

---

## 6. Microfrontend Discovery & Usage

The service exports its frontend component manifest at `/ui/manifest`:

```http
GET /ui/manifest
```

### Manifest Response
```json
{
  "service": "campaign-analytics",
  "package": "@runefoble/campaign-analytics-ui",
  "version": "0.1.0",
  "components": [
    "runefoble-campaign-analytics",
    "runefoble-combat-heatmap",
    "runefoble-chronicle-timeline",
    "runefoble-campaign-telemetry"
  ]
}
```

### Embedding `<runefoble-campaign-analytics>` in the App Shell
```html
<script type="module" src="/services/campaign_analytics/ui/src/index.ts"></script>

<runefoble-campaign-analytics
  campaignId="c-sunken-temple"
  sessionId="sess-03"
  encounterId="enc-grotto-clash"
  apiBaseUrl="http://localhost:8011"
></runefoble-campaign-analytics>
```

### Subcomponents & Storybook Verification
- `<runefoble-combat-heatmap>`: Canvas-based 2D grid overlay visualizing movement corridors, hazard areas, knockouts, and density heatmaps with metric filters (`all`, `damage`, `hit`, `movement`).
- `<runefoble-chronicle-timeline>`: Interactive scrubber with auto-playback and click-to-play audio recap snippets.
- Interactive Storybook stories are co-located in `services/campaign_analytics/ui/src/runefoble-campaign-analytics.stories.ts` with test states for `EmptyState`, `ActiveCombatTelemetry`, `VictoryCelebration`, and `TotalPartyKill`.
