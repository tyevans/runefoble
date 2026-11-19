# How-To: Balance Combat Encounters & Query Rules Compendium

This guide explains how to query canonical SRD 5.1 monsters, spells, and conditions using sub-50ms `redstring` search (BM25 by default, hybrid when an embedding provider is configured), generate mathematically balanced combat encounters with role synergy, register campaign homebrew rules guarded by SpiceDB Zanzibar, and use FastMCP tabletop tools.

---

## 1. Rules Search

Every example calls the gateway at `http://localhost:8000`. The gateway forwards each compendium route to the `rules_compendium` service. Do not call the service port directly. If `rules_compendium` is unreachable, the gateway returns `503`. If it returns a 5xx, the gateway returns `502`.

To query rules, spells, conditions, or monsters. Set `TOKEN` to a Zitadel access token. Every compendium route except health and OpenAPI requires a verified bearer token. A request with no token returns `401`.

```bash
curl -G http://localhost:8000/api/v1/compendium/rules/search \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "query=fire damage explosion" \
  --data-urlencode "limit=5"
```

To include homebrew from a campaign, add `campaign_id`. The search returns a homebrew rule only when the caller passes `homebrew_rule.view` for that rule. A campaign viewer passes this check. The rule author passes it too. Any other caller gets SRD results only.

### Response
```json
{
  "query": "fire damage explosion",
  "results_count": 2,
  "took_ms": 1.25,
  "retrieval_mode": "lexical",
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

### Retrieval Modes

The `retrieval_mode` field states how the service ranked the results.

| Mode | Ranking | When it applies |
|---|---|---|
| `lexical` | BM25 keyword match only. A query that shares no keyword with a rule does not find it. | No embedding provider is configured. This is the default. |
| `hybrid` | BM25 fused with vector search from the configured provider. | `RUNEFOBLE_RULES_EMBEDDING=openai_compatible`. |

To enable `hybrid` mode, set the variables in [Platform Services](../reference/platform-services.md#rules-compendium-retrieval-mode). The provider contract is in [Embedding Providers](../reference/embedding-providers.md).

In `lexical` mode the endpoint answers in under 50 ms for real-time voice arbitration and DM rule verification. In `hybrid` mode, the embedding call adds the provider latency.

---

## 2. Direct Monster & Condition Lookups

Retrieve specific canonical stat blocks or condition mechanics by name:

```bash
# Retrieve monster stat block
curl http://localhost:8000/api/v1/compendium/monsters/Goblin \
  -H "Authorization: Bearer $TOKEN"

# Retrieve condition mechanics
curl http://localhost:8000/api/v1/compendium/conditions/Paralyzed \
  -H "Authorization: Bearer $TOKEN"
```

A homebrew monster is read the same way, with the campaign named. The caller must pass `homebrew_rule.view` for it. Otherwise the route returns `404`, the same as for a missing monster. Spell and condition lookups return SRD entries only.

```bash
curl "http://localhost:8000/api/v1/compendium/monsters/Abyssal%20Shadowstalker?campaign_id=8a329ef2-5c91-4cf1-83d8-21d4bb67f101" \
  -H "Authorization: Bearer $TOKEN"
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
curl -X POST http://localhost:8000/api/v1/compendium/encounters/balance \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
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

When the request names a `campaign_id`, the caller needs `campaign.play` on that campaign. Otherwise the route returns `403`. A request with no `campaign_id` needs only a verified token.

The balancing engine:
1. Calculates aggregate party XP thresholds for Easy, Medium, Hard, and Deadly tiers based on 5e rules.
2. Applies action economy multipliers scaled for monster count and adjusted for small (<3) or large (>=6) party sizes.
3. Selects synergistic combinations balancing frontline brutes, ranged artillery, and controllers.
4. Emits `runefoble.events.compendium.encounter_balanced` event on `EncounterAggregate`.

---

## 4. Registering Campaign Homebrew Rules

To register custom monsters or rules restricted to a campaign. Set `DM_TOKEN` to a Zitadel access token for the DM. rules_compendium takes the author from the verified token subject and ignores any `author_id` in the body. A request with no valid token returns `401`.

```bash
curl -X POST http://localhost:8000/api/v1/compendium/homebrew \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DM_TOKEN" \
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

SpiceDB Zanzibar enforces that only authorized DMs or campaign owners (`run_session` or `manage`) can register homebrew rules. A caller without that grant gets `403`. The server writes the `homebrew_rule#campaign` and `homebrew_rule#author` relations before it saves the rule. A failed write returns `503`, and the rule is not saved.

Homebrew rules are stored in the campaign aggregate. The event store is the source of truth. The service indexes each rule into campaign-isolated `redstring` storage at start-up and on each registration. A restart keeps every registered rule. Homebrew never writes to the SRD entries.

The list route `GET /api/v1/compendium/homebrew/{campaign_id}` and the campaign search return a rule only when the caller passes `homebrew_rule.view`. A stranger gets an empty list and SRD results only.

A homebrew rule whose name matches an SRD entry is `shadowed`. The list route marks it with `"shadowed": true`. Lookup and search return the SRD entry for that name, never the homebrew rule.

---

## 5. FastMCP Tabletop Tools

LLM agents and The Watcher can call compendium tools through the MCP server. Use the public MCP client protocol. `session` is an initialized MCP `ClientSession` on the `/mcp` endpoint, with the caller bearer:

```python
# Look up monster stat block
res = await session.call_tool("query_monster_stat_block", {"monster_name": "Bugbear"})

# Calculate encounter balance
enc = await session.call_tool(
    "calculate_encounter_balance",
    {"party_levels": [4, 4, 4], "target_difficulty": "Hard"},
)
```

---

## 6. Microfrontend Integration (`<runefoble-rules-compendium>`)

Per ADR-0013, `services/rules_compendium/ui/` vendors Lit Web Components that can be embedded into the App Shell or used standalone:

### Manifest Discovery

The gateway does not proxy `/ui/manifest`. The `rules_compendium` service serves its manifest on its own port. See the [Ports and Endpoints reference](../reference/ports-and-endpoints.md) for the cluster address.

```json
{
  "service": "rules_compendium",
  "package": "@runefoble/rules-compendium-ui",
  "version": "0.1.0",
  "components": [
    "runefoble-rules-compendium",
    "runefoble-rules-lookup",
    "runefoble-encounter-builder",
    "runefoble-homebrew-creator"
  ]
}
```

### Embedding in HTML / App Shell
```html
<runefoble-rules-compendium
  apiBaseUrl="http://localhost:8000"
  campaignId="8a329ef2-5c91-4cf1-83d8-21d4bb67f101"
  userId="dm-evelyn-1"
  isDM="true"
></runefoble-rules-compendium>

<!-- Or embed modular subviews directly: -->
<runefoble-homebrew-creator
  apiBaseUrl="http://localhost:8000"
  campaignId="8a329ef2-5c91-4cf1-83d8-21d4bb67f101"
  userId="dm-evelyn-1"
  isDM="true"
></runefoble-homebrew-creator>
```

### Key Features:
- **Instant Hybrid Search**: Debounced autocomplete with sub-50ms latency badge and category filter pills (`ALL`, `MONSTER`, `SPELL`, `CONDITION`, `HOMEBREW`).
- **Interactive CR Encounter Builder**: Dynamic XP threshold computation across party levels/sizes with real-time lethality calculation and 1-click Auto-Balance.
- **Homebrew Forge Subview**: Dedicated `<runefoble-homebrew-creator>` component with form validation against compendium schemas guarded by SpiceDB Zanzibar authorization.
- **Modular Sub-Stylesheets**: Tokenized CSS modules under `src/styles/` (`compendium-base.styles.ts`, `encounter-builder.styles.ts`, `homebrew-form.styles.ts`) strictly < 150 lines per Hard Invariant 6 and ADR-0013.


