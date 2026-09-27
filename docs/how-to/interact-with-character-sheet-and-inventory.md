# How-To: Interact with Character Sheet Inventory, Equipment & Condition Tracker

This guide explains how to use the interactive digital character sheet microfrontend (`<runefoble-character-sheet>`) to equip gear, manage inventory encumbrance, inspect active conditions and absence penalties, and track spell slots.

---

## 1. Visual Paper Doll & Click-to-Equip Interaction

The character sheet provides dedicated interactive paper doll slots for core equipment:
- **`main_hand`**: Weapons, wands, or tools.
- **`off_hand`**: Shields, focuses, or secondary weapons.
- **`armor`**: Light, medium, heavy armor, or mystical robes.
- **`accessory`**: Rings, amulets, or cloaks.

### Equipping & Unequipping
1. **Equip**: Click the **"Equip"** button next to any item in the inventory list. The item is placed in its designated slot and dispatches the `equip-item` CustomEvent (`{ slot, itemName, itemId }`).
2. **Unequip**: Click the red **"✕"** button on any filled paper doll slot. The item returns to general carried inventory and dispatches the `unequip-item` CustomEvent (`{ slot, itemName }`).

---

## 2. Dynamic Encumbrance Capacity Bar

The encumbrance bar dynamically sums the total weight of all carried items (`quantity * weight_lbs`) and compares it against character Strength thresholds:

| Load Tier | Capacity Threshold | Visual Indicator | Movement & Tactical Penalty |
|---|---|---|---|
| **Light** | $\le 33\%$ capacity | Blue (`var(--rf-accent-secondary)`) | None |
| **Medium** | $\le 66\%$ capacity | Teal / Green (`#2a9d8f`) | Normal movement |
| **Heavy** | $\le 100\%$ capacity | Yellow (`var(--rf-accent-tertiary)`) | Speed reduced by 10 ft |
| **Overburdened** | $> 100\%$ capacity | Red (`var(--rf-accent-primary)`) | Speed reduced by 20 ft; disadvantage on Str/Dex checks |

---

## 3. Condition Indicators & Absence Badges

The sheet displays both rules-as-written 5e/d20 tactical conditions and Runefoble absence penalties:
- **Tactical Conditions** (`blinded`, `prone`, `stunned`, `poisoned`, etc.): Rendered with blue geometric badges and tactical icons (`⚡`, `👁️`, `🔻`).
- **Runefoble Absence Penalties** (`drunk`, `foolishness`, `greed`, `cowardice`): Inflicted when human players miss a session and their character is piloted by The Watcher AI stand-in. Rendered with yellow warning badges (`🍺`, `🤡`, `💰`).

### Interactive Tooltips
Hover over or click any condition badge to reveal an informational popover showing:
- Exact mechanical consequences (e.g. "Attack rolls against creature have advantage").
- Saving throw modifiers (e.g. "Disadvantage on Dex saves vs physical pushes").
- Source attribution (e.g. Tactical condition vs DM Absence Penalty).

---

## 4. Spellbook & Spell Slot Tracker

Spellcasters can manage their magical reserves without manual pen-and-paper tracking:
1. **Clickable Pips**: Each spell tier (1 to 9) displays available slots as solid circles (`●`) and expended slots as empty rings (`○`).
   - Click an available slot (`●`) to expend it (dispatches `expend-slot`).
   - Click an expended slot (`○`) to restore it during short/long rests (dispatches `restore-slot`).
2. **Prepared Spells**: Click **"Cast"** next to any prepared spell to expend an appropriate slot tier.
3. **Spellbook Management**: Click **"Prepare"** or **"Unprepare"** in the known spellbook to swap daily prepared spells.

---

## 5. Microfrontend Embedding

```html
<runefoble-character-sheet
  characterId="c-valeros-12"
  apiBaseUrl="/api/v1/characters"
  characterName="Valeros the Bold"
  characterClass="Fighter 4 / Wizard 1"
  .level="${5}"
  .currentHp="${38}"
  .maxHp="${44}"
  .armorClass="${18}"
  .strength="${16}"
  .equipment="${{ main_hand: 'Longsword +1', off_hand: 'Steel Shield', armor: 'Chain Mail' }}"
  @equip-item="${(e) => handleEquip(e.detail)}"
  @unequip-item="${(e) => handleUnequip(e.detail)}"
  @cast-spell="${(e) => handleCast(e.detail)}"
></runefoble-character-sheet>
```

---

## 6. Modular CSS Architecture & Theming

The character sheet's visual styling is modularized into discrete CSS blocks adhering to Bauhaus geometric tokens (`ADR-0004`, `ADR-0012`):
- **Core Styles** (`runefoble-character-sheet.core.styles.ts`): Host layout, typography, character identity banner, and vitals grid.
- **Inventory Styles** (`runefoble-character-sheet.inventory.styles.ts`): Equipment paper doll slots, slot rarity borders, action buttons, and dynamic encumbrance capacity gauge.
- **Conditions Styles** (`runefoble-character-sheet.conditions.styles.ts`): Tactical condition badges, absence penalty tags, interactive tooltips, spell slot pips, and responsive mobile breakpoints.
- **Aggregator** (`runefoble-character-sheet.styles.ts`): Re-exports modular style blocks as a combined `CSSResultGroup` for Lit element consumption.

