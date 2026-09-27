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

### Step 2: Upgrade Facility

```bash
curl -X POST http://localhost:8004/api/v1/campaigns/camp-55/stronghold/upgrade \
  -H "Content-Type: application/json" \
  -d '{
    "facility_id": "watchtower",
    "gold_spent": 100,
    "materials_spent": {"wood": 20}
  }'
```

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

## 5. Modular Alchemical Domain Architecture

Under TASK-0153 (ADR-0003, ADR-0007, ADR-0011), the crafting engine is organized into focused submodules under `services/character_sheet/src/character_sheet/crafting/`:

- **`recipes.py`**: Reagents, catalysts, canonical recipes, `Recipe` schema, `CraftingState`, and DC calculation (`calculate_crafting_dc`).
- **`mishaps.py`**: Volatile mishap d100 tables, risk calculation (`calculate_volatile_risk`), and `MishapResolver` consequence generator.
- **`engine.py`**: `CraftingEngine` (proficiency application and recipe evaluation) and `CraftingAggregate` event-sourced state transitions.
- **`__init__.py`**: Re-exports all core domain types (`CraftingEngine`, `Recipe`, `MishapResolver`, `CraftingAggregate`).
- **`crafting.py`**: Backward-compatible facade preserving all top-level module imports.

---

## 6. Modular Blackbox Test Suite Architecture

Under TASK-0184 (ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 6), the blackbox test suite is organized into focused submodules under `tests/test_blackbox_campfire_crafting/`:

- **`conftest.py`**: Shared test harness, `MockSpiceDBClient`, `MockAsyncRedis`, and FastAPI `TestClient` fixtures (< 70 lines).
- **`test_recipe_crafting.py`**: Public reagent catalogs, recipe combinations, inventory synchronization, and Zanzibar authorization (< 150 lines).
- **`test_volatile_mishaps.py`**: Volatile reaction failure thresholds, explosion events, and setback condition effects (< 110 lines).
- **`test_campfire_boons.py`**: Stronghold upgrades, resting storytelling prompts, camaraderie boons, and Lit microfrontend manifest (< 150 lines).

