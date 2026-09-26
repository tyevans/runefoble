# How-To: Balance Combat Encounters & Query Rules Compendium

This guide explains how to query canonical SRD 5.1 monsters, spells, and conditions using sub-50ms `redstring` hybrid search, generate mathematically balanced combat encounters with role synergy, register campaign homebrew rules guarded by SpiceDB Zanzibar, and use FastMCP tabletop tools.

---

## 1. Hybrid Rules Search

To query rules, spells, conditions, or monsters with combined BM25 lexical keyword matching and semantic vector retrieval:

```bash
curl -G http://localhost:8007/api/v1/compendium/rules/search \
  --data-urlencode "query=fire damage explosion" \
  --data-urlencode "limit=5"
```

### Response
```json
{
  "query": "fire damage explosion",
  "results_count": 2,
  "took_ms": 1.25,
  "results": [
    {
      "category": "spell",
      "name": "Fireball",
      "score": 0.88,
      "summary": "Fireball (Level 3 Evocation spell): Casting time: 1 action, Range: 150 feet...",
      "details": {
        "level": 3,
        "school": "Evocation",
        "damage": "8d6 fire"
      },
      "is_homebrew": false,
      "campaign_id": null
    }
  ]
}
```

The endpoint guarantees sub-50ms response times for real-time voice arbitration and DM rule verification.

---

## 2. Direct Monster & Condition Lookups

Retrieve specific canonical stat blocks or condition mechanics by name:

```bash
# Retrieve monster stat block
curl http://localhost:8007/api/v1/compendium/monsters/Goblin

# Retrieve condition mechanics
curl http://localhost:8007/api/v1/compendium/conditions/Paralyzed
```

### Monster Response
```json
{
  "name": "Goblin",
  "challenge_rating": 0.25,
  "creature_type": "humanoid",
  "size": "Small",
  "armor_class": 15,
  "hit_points": 7,
  "speed": "30 ft.",
  "xp": 50,
  "role": "skirmisher",
  "stats": {"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8}
}
```

---

## 3. Automated CR Encounter Balancing

To calculate XP budgets and recommend a synergistic enemy combat group for a party:

```bash
curl -X POST http://localhost:8007/api/v1/compendium/encounters/balance \
  -H "Content-Type: application/json" \
  -d '{
    "party_levels": [3, 3, 3, 3],
    "target_difficulty": "Medium"
  }'
```

### Response
```json
{
  "encounter_id": "93f66bf8-1678-433b-8515-8fa9074dcfc1",
  "party_levels": [3, 3, 3, 3],
  "party_size": 4,
  "target_difficulty": "Medium",
  "difficulty_tier": "Medium",
  "total_party_xp_threshold": {
    "easy": 300,
    "medium": 600,
    "hard": 900,
    "deadly": 1600
  },
  "monsters": [
    {
      "name": "Bugbear",
      "cr": 1.0,
      "xp": 200,
      "count": 1,
      "role": "brute",
      "subtotal_xp": 200
    },
    {
      "name": "Goblin",
      "cr": 0.25,
      "xp": 50,
      "count": 2,
      "role": "skirmisher",
      "subtotal_xp": 100
    }
  ],
  "total_monster_count": 3,
  "total_raw_xp": 300,
  "multiplier": 2.0,
  "adjusted_xp": 600,
  "tactical_summary": "Balanced Medium encounter (600 adjusted XP, 2.0x multiplier) featuring 3 combatants with tactical synergy across brute, skirmisher."
}
```

The balancing engine:
1. Calculates aggregate party XP thresholds for Easy, Medium, Hard, and Deadly tiers based on 5e rules.
2. Applies action economy multipliers scaled for monster count and adjusted for small (<3) or large (>=6) party sizes.
3. Selects synergistic combinations balancing frontline brutes, ranged artillery, and controllers.
4. Emits `EncounterBalanced` event on `EncounterAggregate`.

---

## 4. Registering Campaign Homebrew Rules

To register custom monsters or rules restricted to a campaign:

```bash
curl -X POST http://localhost:8007/api/v1/compendium/homebrew \
  -H "Content-Type: application/json" \
  -H "x-user-id: dm-evelyn-1" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "rule_type": "monster",
    "title": "Abyssal Shadowstalker",
    "content": {
      "challenge_rating": 3.0,
      "creature_type": "fiend",
      "size": "Medium",
      "armor_class": 16,
      "hit_points": 45,
      "xp": 700,
      "role": "skirmisher",
      "description": "A stealthy fiend summoned from the Shadowfell."
    }
  }'
```

SpiceDB Zanzibar enforces that only authorized DMs or campaign owners (`run_session` or `manage`) can register homebrew rules. Homebrew rules are indexed into campaign-isolated `redstring` storage and searchable by campaign participants.

---

## 5. FastMCP Tabletop Tools

LLM agents and The Watcher can call compendium tools via FastMCP:

```python
from gateway_mcp.server import mcp

# Look up monster stat block
monster_tool = mcp.get_tool("query_monster_stat_block")
res = await monster_tool.run({"monster_name": "Bugbear"})

# Calculate encounter balance
encounter_tool = mcp.get_tool("calculate_encounter_balance")
enc = await encounter_tool.run({"party_levels": [4, 4, 4], "target_difficulty": "Hard"})
```

---

## 6. Microfrontend Integration (`<runefoble-rules-compendium>`)

Per ADR-0013, `services/rules_compendium/ui/` vendors Lit Web Components that can be embedded into the App Shell or used standalone:

### Manifest Discovery
```bash
curl http://localhost:8007/ui/manifest
```

```json
{
  "service": "rules_compendium",
  "package": "@runefoble/rules-compendium-ui",
  "version": "0.1.0",
  "components": [
    "runefoble-rules-compendium",
    "runefoble-rules-lookup",
    "runefoble-encounter-builder"
  ]
}
```

### Embedding in HTML / App Shell
```html
<runefoble-rules-compendium
  apiBaseUrl="http://localhost:8007"
  campaignId="8a329ef2-5c91-4cf1-83d8-21d4bb67f101"
  userId="dm-evelyn-1"
  isDM="true"
></runefoble-rules-compendium>
```

### Key Features:
- **Instant Hybrid Search**: Debounced autocomplete with sub-50ms latency badge and category filter pills (`ALL`, `MONSTER`, `SPELL`, `CONDITION`, `HOMEBREW`).
- **Interactive CR Encounter Builder**: Dynamic XP threshold computation across party levels/sizes with real-time lethality calculation and 1-click Auto-Balance.
- **Homebrew Forge**: Form validation against compendium schemas guarded by SpiceDB Zanzibar authorization.

