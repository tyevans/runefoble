# How-To: Simulate NPC Faction Agendas and Background World Ticks

This guide explains how Dungeon Masters use The Watcher's autonomous background simulation engine to tick NPC faction agendas between gaming sessions, generating dynamic geopolitical shifts, trade shortages, and evolving tavern rumors (ADR-0002, ADR-0006, ADR-0011, US-0057).

---

## 1. SpiceDB Zanzibar Authorization

Faction management and downtime world ticks are strictly gated by SpiceDB Zanzibar object authorization (`libs/runefoble_auth/schema/runefoble.zed`).

- **Executing World Ticks & Creating Factions**:
  Requires `run_session` permission (or `dungeon_master` / `owner` relation) on the `campaign` resource:
  `campaign:<campaign_id>#run_session@user:<user_id>`.
  Unauthorized players attempting simulation ticks receive HTTP `403 Forbidden`.
- **Viewing Faction Intelligence**:
  Campaign members (players and spectators) can query faction lists and summaries via the `view` permission:
  `campaign:<campaign_id>#view@user:<user_id>`.

```bash
# Execute world progression tick as authorized DM
curl -X POST "http://localhost:8001/api/v1/campaigns/camp-101/world-tick" \
  -H "X-User-Id: dm_evelyn" \
  -H "Content-Type: application/json" \
  -d '{"regional_stability": 55, "random_seed": 42}'
```

---

## 2. Faction Domain Modeling & Aggregate Sourcing

Factions are modeled as event-sourced aggregates (`FactionAggregate` in `services/the_watcher/src/the_watcher/factions.py`), governed by Hard Invariant 2 and ADR-0011.

Key attributes tracked in `FactionState`:
- `faction_id`: Unique identifier (e.g. `faction-ironfang`).
- `name`: Faction name (e.g. "Ironfang Syndicate").
- `influence`: Numeric power level between `1` and `100`.
- `resources`: Faction operational assets and liquid wealth.
- `disposition`: Attitude toward the player party (`hostile`, `unfriendly`, `neutral`, `friendly`, `allied`).
- `active_goal`: Current faction objective (e.g. "Smuggle Arcane Weapons into Oakhaven").
- `goal_progress` & `goal_target`: Progress accumulated toward agenda completion (0 to 100%).
- `rival_faction_ids`: List of conflicting factions whose defense scores counter agenda checks.
- `territory`: Geopolitical sector or stronghold occupied by the faction.

All state mutations occur strictly via domain events registered with `@register_event`:
- `FactionCreated`: Initializes faction aggregate.
- `FactionAgendaSet`: Establishes or redirects the active goal.
- `FactionAgendaAdvanced`: Records d20 check resolution, progress delta, and narrative log.
- `GeopoliticalShiftOccurred`: Dispatched upon agenda completion to signal territorial control changes or market shortages.
- `WorldTickExecuted`: Published to Redis Streams (`runefoble.events.watcher`) summarizing the cycle.

---

## 3. Probabilistic Simulation Tick Engine

When a world tick is triggered:
1. **Rival Counter-Measures**: If a faction has designated rivals, the highest rival influence provides defense resistance against the check.
2. **Regional Stability Modifiers**:
   - Subversive agendas (smuggling, infiltration, sabotage) encounter higher DCs in high-stability regions due to heightened watch alertness.
   - Legitimate or defensive agendas benefit from stable regional administration.
3. **Resolution Checks**:
   - A d20 roll plus modifiers `(influence // 10) + (resources // 20)` is checked against the dynamic DC.
   - Outcomes include `success` (+25-35% progress), `partial_success` (+10% progress), `countered` (-10% progress from rival interception), and `failure` (stalled).
4. **Geopolitical Shifts & Ripple Effects**:
   - When `goal_progress >= goal_target` (100%), the faction triggers a `GeopoliticalShiftOccurred` event.
   - Effects propagate into trade shortages (weapon markups), martial law (curfews), or territorial capture.
5. **Evolving Tavern Rumors**:
   - Each tick extracts ambient gossip hooks that DMs can feed to player characters during tavern visits.

---

## 4. Public REST API Reference

### Trigger Downtime World Tick
```http
POST /api/v1/campaigns/{campaign_id}/world-tick
X-User-Id: dm_evelyn
Content-Type: application/json

{
  "regional_stability": 50,
  "random_seed": 108,
  "ticks": 1,
  "custom_rumors": ["Caravans from the eastern gate have stopped arriving."]
}
```

*Alias endpoint: `POST /api/v1/campaigns/{campaign_id}/factions/tick`*

### Register Custom Faction
```http
POST /api/v1/campaigns/{campaign_id}/factions
X-User-Id: dm_evelyn
Content-Type: application/json

{
  "name": "Cult of the Shadow Serpent",
  "influence": 60,
  "resources": 45,
  "disposition": "hostile",
  "active_goal": "Corrupt Oakhaven Aqueduct",
  "territory": "Subterranean Catacombs",
  "rival_faction_ids": []
}
```

### Query Campaign Factions
```http
GET /api/v1/campaigns/{campaign_id}/factions
X-User-Id: player_valeros
```

### Retrieve Latest DM Intelligence Bulletin
```http
GET /api/v1/campaigns/{campaign_id}/world-ticks/latest
X-User-Id: dm_evelyn
```

---

## 5. Sample DM Intelligence Bulletin

```markdown
# 📜 THE WATCHER INTELLIGENCE BULLETIN: WORLD TICK #1
**Campaign**: `camp-101` | **Regional Stability**: 55/100

## ⚔️ Geopolitical & Territorial Shifts
- **[Oakhaven Docks] TRADE_SHORTAGE**: Ironfang Syndicate flooded Oakhaven Docks with black-market contraband, triggering trade shortages.

## 🏛️ Faction Agenda Progress
- **Ironfang Syndicate** (Influence: 62, Resources: 56)
  - *Active Agenda*: Smuggle Arcane Weapons into Oakhaven
  - *Progress*: 100/100%
- **Arcane Order** (Influence: 72, Resources: 66)
  - *Active Agenda*: Infiltrate Arcane Guild Archives
  - *Progress*: 25/100%

## 🍻 Evolving Tavern Rumors (Player Feed Hooks)
- *"Overheard at tavern: 'Ironfang Syndicate flooded Oakhaven Docks with black-market contraband. Watch yourself if you head toward Oakhaven Docks.'"*
- *"Tavern gossip: 'Arcane Order agents were active around High Spire.'"*

## 👁️ The Watcher's Tactical Advisory
- **Board State Ripple**: Update token presence and sentry crests in affected sectors.
- **Merchant Cues**: Adjust goods availability and markups based on regional trade flow.
- **NPC Dialogue**: Spoken interactions should mirror current tavern gossip and suspicion.
```
