# How-To: Project Campaign Analytics & Chronicle Timeline

This guide explains how to project combat telemetry, query tactical damage heatmaps, evaluate encounter MVP statistics, and retrieve campaign milestone chronicles using the `services/campaign_analytics` bounded context microservice (ADR-0001, ADR-0003, ADR-0005, ADR-0006, ADR-0011, ADR-0013).

---

## 1. Architecture & Telemetry Pipeline

The Campaign Analytics microservice operates as a CQRS projection engine and chronicle archive:

1. **Redis Streams Ingestion**: The `campaign_analytics_worker` runs one consumer per stream:
   - `runefoble.events.session`: Session lifecycle and encounter progression (`runefoble.events.session.created`, `runefoble.events.session.combat_encounter_started`, `runefoble.events.session.initiative_turn_advanced`, `runefoble.events.session.ended`). Each `runefoble.events.session.initiative_turn_advanced` counts a turn for its active combatant. A round milestone is recorded when the round number changes.
   - `runefoble.events.board`: Token placement and movement (`runefoble.events.board.token_placed`, `runefoble.events.board.token_moved`).
   - `runefoble.events.character`: Damage and healing deltas (`runefoble.events.character.health_changed`). The event carries `session_id` and `campaign_id`. A health change with a null `session_id` is skipped. The character id never stands in for a session.
   - `runefoble.events.watcher`: Dice rolls (`DiceRolled`) and absentee recaps (`AbsenteeRecapGenerated`).
2. **PostgreSQL Read Models**: Every query reads these tables. The service does not keep read models in memory.
   - `campaign_spatial_telemetry`: Heatmap points.
   - `combat_performance_records`: One row per combatant per session. The MVP route reads it.
   - `campaign_timeline_milestones`: Chronicle milestones.
   - `campaign_session_map`: Session to campaign mapping. Events without a campaign id use it.
   - `analytics_projection_state`: Token positions, names, and the active combatant and encounter. It also holds each stream's last projected message id.
   - SQLite and in-memory stores are not supported. The service refuses to start on a non-PostgreSQL URL.
3. **Transactional Projection and Resume**: Each stream message is projected in one database transaction. The transaction also stores that message id as the stream position. A failed write rolls back the whole message. The message goes to `{stream}.dlq` and the consumer continues. On start-up, each stream resumes after its stored position. Replayed rows keep the same ids, so a replay does not create duplicate rows. A replayed milestone reuses its saved chronicle event, so the timeline holds one row per milestone.
4. **Chronicle Aggregate for Milestones**: Each milestone is recorded on `CampaignChronicleAggregate` (`eventsource-py`) through `AggregateRepository`. The event store saves the `ChronicleMilestoneRecorded` event first. The milestone row is projected from the saved event. The row id is the saved event's id. A milestone that a replay finds already saved is reused, not recorded again. The MVP and telemetry snapshot events (`EncounterMvpAwarded`, `CombatTelemetrySnapshotCreated`) are defined but not produced. MVP scores are computed from `combat_performance_records` at query time.
5. **Start-up and Store Failures**:
   - Start-up fails when PostgreSQL is unreachable or the tables cannot be created. The service raises `CampaignStoreStartupError` and does not serve requests. No in-memory store is used.
   - Start-up fails when Redis is unreachable. The service raises `EventBusUnavailableError` and does not serve requests.
   - A query that cannot reach PostgreSQL returns HTTP `503` with `{"detail": "Campaign analytics store is unavailable"}`. It never returns empty data.
   - `/healthz` reports each consumer as `running` or `failed`. It returns `503` when a consumer fails.

```
Redis Streams ───► CampaignAnalyticsWorker ───► AnalyticsEventDispatcher ───► ProjectionTx (one transaction)
                                                                                    │
                                                                                    ▼
Zanzibar Auth ───► FastAPI APIRouters ◄──────────────────────────────────────── Analytics Queries
                   ├─ /heatmap                                                     ├─ spatial.py
                   ├─ /mvp                                                         ├─ mvp.py
                   └─ /timeline                                                    └─ timeline.py
```

---

## 2. SpiceDB Zanzibar Object Authorization

Access to campaign analytics and chronicle records is protected by SpiceDB Zanzibar object permissions (`libs/runefoble_auth/schema/runefoble.zed`):

- **Permission**: Every read route checks the schema permission `campaign.view` on the target campaign (`campaign:<campaign_id>`). The service never checks a relation name as a permission.
- **Relations**: Users holding the `owner`, `dungeon_master`, `game_master`, `player`, or `spectator` relation inherit `view`. Membership comes from the invite frontdoor.
- Callers without a verified bearer token receive HTTP `401 Unauthorized`. There is no public view.
- Authenticated callers without the `view` permission receive HTTP `403 Forbidden`.
- If SpiceDB cannot answer, the service returns HTTP `503` with `{"detail": "Authorization service is unavailable"}`. It never returns data or a denial for a failed check.

When querying endpoints, send the Zitadel JWT as a bearer token. The gateway verifies the token and forwards the same `Authorization` header to the analytics service. The gateway ignores any `X-User-Id` header from the client.

```http
GET /api/v1/analytics/campaigns/c5f8742d-cfca-4fbc-8911-37d363b9f4a1/heatmap
Authorization: Bearer <zitadel-jwt>
```

---

## 3. Querying Spatial Damage Heatmaps

The heatmap endpoint aggregates token coordinates, hit frequencies, and damage densities across combat rounds:

```http
GET /api/v1/analytics/campaigns/{campaign_id}/heatmap?cell_size=5&metric=all&session_id={optional_session_id}
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
      "id": "m1",
      "campaign_id": "c5f8742d-cfca-4fbc-8911-37d363b9f4a1",
      "session_id": "sess-01",
      "type": "session_recap",
      "title": "Session 1 Concluded",
      "description": "Party defeated the Goblin Ambush and recovered the Sunstone",
      "timestamp": "2026-09-26T14:00:00Z",
      "metadata": {"summary": "Party defeated the Goblin Ambush and recovered the Sunstone"}
    },
    {
      "id": "m2",
      "campaign_id": "c5f8742d-cfca-4fbc-8911-37d363b9f4a1",
      "session_id": "sess-02",
      "type": "boss_encounter",
      "title": "Defeat of the Red Dragon",
      "description": "Party vanquished Ignis the Terrible at Dragon's Peak",
      "timestamp": "2026-09-26T15:30:00Z",
      "metadata": {}
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
The element makes no network calls. The App Shell loads the three datasets through the gateway with the signed-in user's bearer token, then passes them in as properties. If any read fails, the Chronicle & Stats tab shows the error state with retry.

Gateway routes read by the App Shell (`frontend/src/services/campaign-hub-client.ts`):

| Gateway route | Property | Source service |
|---|---|---|
| `GET /api/v1/analytics/campaigns/{campaign_id}/heatmap` | `.heatmapData` | `campaign_analytics` (port 8011) |
| `GET /api/v1/analytics/campaigns/{campaign_id}/mvp` | `.mvpData` | `campaign_analytics` (port 8011) |
| `GET /api/v1/analytics/campaigns/{campaign_id}/timeline` | `.timelineData` | `campaign_analytics` (port 8011) |

```html
<script type="module" src="/services/campaign_analytics/ui/src/index.ts"></script>

<runefoble-campaign-analytics
  campaignId="c-sunken-temple"
  .heatmapData=${heatmap}
  .mvpData=${mvp}
  .timelineData=${timeline}
></runefoble-campaign-analytics>
```

### Subcomponents & Storybook Verification
- `<runefoble-combat-heatmap>`: Canvas-based 2D grid overlay visualizing movement corridors, hazard areas, knockouts, and density heatmaps with metric filters (`all`, `damage`, `hit`, `movement`). Decomposed into modular delegates under `services/campaign_analytics/ui/src/heatmap/`:
  - `canvas-renderer.ts`: Pure 2D canvas drawing routines (grid lines, cell density gradients, movement corridor vectors, hazard callouts, knockout glyphs).
  - `heatmap-controls.template.ts`: Metric filter buttons (`all`, `damage`, `hit`, `movement`), legend gradient scale, and event summary statistics.
  - `cell-inspector.template.ts`: Hovered/selected coordinate card, damage breakdown, and casualty listings.
- `<runefoble-chronicle-timeline>`: Interactive scrubber with auto-playback and click-to-play audio recap snippets.
- Interactive Storybook stories are co-located in `services/campaign_analytics/ui/src/runefoble-campaign-analytics.stories.ts` (with reusable mock datasets modularized in `services/campaign_analytics/ui/src/fixtures/campaign-analytics.fixtures.ts`) and `services/campaign_analytics/ui/src/runefoble-combat-heatmap.stories.ts` with test states for `DefaultAllWeights`, `DamageFilter`, `StrikesFilter`, `TrafficMovementFilter`, `EmptyState`, `ActiveCombatTelemetry`, `VictoryCelebration`, and `TotalPartyKill`.

---

## 7. Modular Blackbox Verification Suite

The Campaign Analytics UI test suite is decomposed into focused frontdoor modules under `tests/test_blackbox_campaign_analytics_ui/` maintaining Hard Invariant 6 (< 500 lines per file):

- `tests/test_blackbox_campaign_analytics_ui/test_analytics_dashboard_ui.py`: Verifies microfrontend manifest advertising (`GET /ui/manifest`), component package export and forwarding, Storybook scenario coverage, and REST frontdoor MVP turn metrics delivery.
- `tests/test_blackbox_campaign_analytics_ui/test_chronicle_timeline_ui.py`: Verifies `<runefoble-chronicle-timeline>` Custom Element decorator integrity, living chronicle milestone frontdoor binding, absentee recap metadata, milestone pagination limits, and session filtering.
- `tests/test_blackbox_campaign_analytics_ui/test_spatial_heatmaps_ui.py`: Verifies `<runefoble-combat-heatmap>` Custom Element decorator, modular file boundary budgets (< 120 lines controller, < 120 lines canvas-renderer, < 90 lines controls, < 80 lines inspector), 2D canvas damage density matrix calculations, grid coordinate overlays, metric filter parameters, and SpiceDB Zanzibar campaign object authorization.

