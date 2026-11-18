# How-To: Run Campfire Rests & Alchemical Crafting

This guide explains how to initiate interactive campfire rest interludes with collaborative storytelling prompts, experiment with alchemical reagents in the crucible laboratory, resolve volatile risk tables, and fortify persistent campsites with team resting boons (TASK-0100 / PRD-0014 / US-0044).

---

## 1. Alchemical Reagent Experimentation & Transmutation

Artisans like Bram the Tinkerer can combine harvested monster parts, flora, and mineral extracts in the alchemical workbench.

### Step 1: Inspect Available Reagents & Catalysts

Query the alchemical catalog to discover affinities, instability ratings, and known recipes:

```bash
curl http://localhost:8003/api/v1/crafting/reagents
curl http://localhost:8003/api/v1/crafting/recipes
```

### Step 2: Combine Reagents in the Crucible

Post a reagent combination to `POST /api/v1/crafting/recipes/combine`:

```bash
curl -X POST http://localhost:8003/api/v1/crafting/recipes/combine \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "c1a84f33-1b03-4f51-b8d2-97ba6c3b9991",
    "reagents": ["Glowmoss Extract", "Volcano Ash"],
    "catalyst": "purified_water"
  }'
```

### Response
```json
{
  "outcome": "success",
  "item_name": "Radiant Smoke Pellet",
  "recipe_name": "Radiant Smoke Pellet",
  "quantity": 1,
  "tags": ["consumable", "radiant", "obscurement", "aoe"],
  "properties": {
    "radius_ft": 20,
    "duration_rounds": 3,
    "save_type": "none"
  },
  "risk_score": 0.15,
  "reagents_consumed": ["Glowmoss Extract", "Volcano Ash"],
  "catalyst_consumed": "purified_water"
}
```

The crafted item is automatically added to the character's inventory in `CharacterAggregate`, deducting consumed ingredients.

### Volatile Mishaps
When volatile reagents are combined without stabilizing catalysts or exceeding risk thresholds, a mishap occurs:
```json
{
  "outcome": "mishap",
  "mishap": {
    "mishap_type": "minor_explosion",
    "severity": "minor",
    "damage": 4,
    "description": "A sharp bang fills the laboratory! Soot covers the crucible and singes eyebrows."
  },
  "risk_score": 0.65,
  "character_current_hp": 20
}
```
Mishap damage and status conditions (e.g. `poisoned`, `blinded`) are directly applied to the character sheet.

Mishap damage publishes `runefoble.events.character.health_changed` and `CharacterDamaged` on the character stream. These are the same events that `POST /api/v1/characters/{id}/health` publishes.

If the character does not exist, the route answers `404`. If the event store fails, the route answers `503`. In both cases nothing is saved.

---

## 2. Campfire Rest Interludes & Collaborative Storytelling

Non-combat rest periods are transformed into rich roleplay interludes rather than skipped spreadsheets.

### Step 1: Query Storytelling Prompts

```bash
curl http://localhost:8004/api/v1/sessions/session-101/rest/prompts
```

### Step 2: Initiate Campfire Rest

```bash
curl -X POST http://localhost:8004/api/v1/sessions/session-101/rest/campfire \
  -H "Content-Type: application/json" \
  -d '{
    "rest_type": "long",
    "storytelling_prompt": "Tell of the first monster that truly frightened your character."
  }'
```

### Response
```json
{
  "session_id": "session-101",
  "rest_type": "long",
  "storytelling_prompt": "Tell of the first monster that truly frightened your character.",
  "boons_applied": [
    "Campfire Camaraderie (+1 Morale to Initiative)",
    "Long Rest Rejuvenation (Full HP Restored)",
    "Spell Slots Recharged",
    "Exhaustion Cleared",
    "Vigilant Sentry (+2 Passive Perception)"
  ],
  "participants_healed": ["Bram the Tinkerer", "Valeros", "Kyra"],
  "status": "completed"
}
```

---

## 3. Persistent Campsite & Stronghold Fortifications

Parties invest gold and raw materials into campsite upgrades that grant persistent mechanical resting bonuses.

### Step 1: Inspect Campsite Facilities

```bash
curl http://localhost:8004/api/v1/campaigns/camp-55/stronghold
```

The treasury starts at zero. Fund it before you upgrade.

### Step 2: Fund the Treasury

Gold and materials enter the stronghold only through this route. Only a DM or stronghold manager can deposit (`stronghold.manage`), because a deposit creates resources. A player gets `403`.

```bash
curl -X POST http://localhost:8004/api/v1/campaigns/camp-55/stronghold/deposit \
  -H "Content-Type: application/json" \
  -d '{
    "gold": 500,
    "materials": {"wood": 40}
  }'
```

The route answers `200` with the new state. It answers `400` when a value is negative or when the deposit adds nothing.

### Step 3: Upgrade Facility

```bash
curl -X POST http://localhost:8004/api/v1/campaigns/camp-55/stronghold/upgrade \
  -H "Content-Type: application/json" \
  -d '{"facility_id": "watchtower"}'
```

The request names the facility only. The tier table sets the gold and materials. A Tier 1 watchtower costs 100 gold and 20 wood. The upgrade subtracts that cost from the treasury and the material store. When the treasury holds too little gold, or the store holds too little of a material, the route answers `409 Conflict`. The `detail` field names each shortfall. A refused upgrade records no event, and the stores do not change.

A request that names a cost, such as `gold_spent` or `materials_spent`, answers `422 Unprocessable Entity`. It records no event.

### Upgrades Catalog:
1. **Watchtower**:
   - Tier 1: `Vigilant Sentry (+2 Passive Perception)`
   - Tier 2: `Vantage Scouting (Advantage on Initiative)`
   - Tier 3: `Impenetrable Ramparts (Ambush Immunity)`
2. **Herbal Drying Rack**:
   - Tier 1: `Restorative Brews (+1d4 Rest Healing)`
   - Tier 2: `Alchemical Affinity (+15% Crafting Stability)`
   - Tier 3: `Reagent Harvest (Free Rare Reagent)`
3. **Arcane Forge**:
   - Tier 1: `Honed Blades (+1 Weapon Damage on first encounter)`
   - Tier 2: `Reinforced Armor (+1 AC for first encounter)`
   - Tier 3: `Artisan Mastery (Equipment Infusions)`

---

## 4. Using the `<runefoble-campfire-crafting>` Web Component

Embed the service-vendored Lit element in the client application shell:

```html
<runefoble-campfire-crafting
  session-id="session-101"
  campaign-id="camp-55"
  character-id="char-bram"
  character-name="Bram the Tinkerer"
  rest-type="long"
></runefoble-campfire-crafting>
```

Listen for custom events:
```javascript
const el = document.querySelector('runefoble-campfire-crafting');

el.addEventListener('reagents-combined', (e) => {
  console.log('Crafting outcome:', e.detail.outcome);
});

el.addEventListener('stronghold-upgrade-requested', (e) => {
  console.log('Upgrading facility:', e.detail.facility);
});
```

---
