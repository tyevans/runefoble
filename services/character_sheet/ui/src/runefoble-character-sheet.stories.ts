import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-character-sheet.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCharacterSheet',
  component: 'runefoble-character-sheet',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const Healthy: Story = {
  render: () => html`
    <runefoble-character-sheet
      characterName="Valeros the Bold"
      characterClass="Fighter Lvl 4"
      .level=${4}
      .currentHp=${38}
      .maxHp=${38}
      .armorClass=${18}
      .initiative=${2}
      .speed=${30}
      .strength=${16}
      .isAiStandIn=${false}
      .equipment=${{
        main_hand: 'Longsword +1',
        off_hand: 'Steel Shield',
        armor: 'Chain Mail',
        accessory: 'Cloak of Protection',
      }}
      .inventory=${[
        { item_id: 'i1', name: 'Longsword +1', quantity: 1, weight_lbs: 3.0, slot: 'main_hand' },
        { item_id: 'i2', name: 'Steel Shield', quantity: 1, weight_lbs: 6.0, slot: 'off_hand' },
        { item_id: 'i3', name: 'Chain Mail', quantity: 1, weight_lbs: 55.0, slot: 'armor' },
        { item_id: 'i4', name: 'Cloak of Protection', quantity: 1, weight_lbs: 1.0, slot: 'accessory' },
        { item_id: 'i5', name: 'Health Potion', quantity: 2, weight_lbs: 0.5 },
      ]}
      .conditions=${[]}
      .penalties=${{}}
      .spellSlots=${{ 1: 0 }}
      .maxSpellSlots=${{ 1: 0 }}
      .preparedSpells=${[]}
      .spellbook=${[]}
    ></runefoble-character-sheet>
  `,
};

export const Encumbered: Story = {
  render: () => html`
    <runefoble-character-sheet
      characterName="Gimli Stonebreaker"
      characterClass="Fighter Lvl 3"
      .level=${3}
      .currentHp=${32}
      .maxHp=${34}
      .armorClass=${17}
      .initiative=${-1}
      .speed=${25}
      .strength=${14}
      .equipment=${{
        main_hand: 'Greataxe',
        armor: 'Full Plate',
      }}
      .inventory=${[
        { item_id: 'e1', name: 'Full Plate', quantity: 1, weight_lbs: 65.0, slot: 'armor' },
        { item_id: 'e2', name: 'Greataxe', quantity: 1, weight_lbs: 7.0, slot: 'main_hand' },
        { item_id: 'e3', name: 'Gold Ingots Chest', quantity: 1, weight_lbs: 80.0 },
        { item_id: 'e4', name: 'Mining Anvil', quantity: 1, weight_lbs: 50.0 },
      ]}
      .conditions=${[]}
    ></runefoble-character-sheet>
  `,
};

export const Afflicted: Story = {
  render: () => html`
    <runefoble-character-sheet
      characterName="Kyra the Sun Maiden"
      characterClass="Cleric Lvl 4"
      .level=${4}
      .currentHp=${8}
      .maxHp=${32}
      .armorClass=${16}
      .initiative=${0}
      .speed=${25}
      .strength=${12}
      .isAiStandIn=${true}
      .equipment=${{
        main_hand: 'Mace',
        off_hand: 'Holy Symbol Shield',
        armor: 'Scale Mail',
      }}
      .inventory=${[
        { item_id: 'a1', name: 'Mace', quantity: 1, weight_lbs: 4.0, slot: 'main_hand' },
        { item_id: 'a2', name: 'Holy Symbol Shield', quantity: 1, weight_lbs: 6.0, slot: 'off_hand' },
        { item_id: 'a3', name: 'Scale Mail', quantity: 1, weight_lbs: 45.0, slot: 'armor' },
      ]}
      .conditions=${[
        {
          id: 'c1',
          name: 'blinded',
          source: 'tactical',
          description: 'Cannot see; attack rolls against have advantage, creature attacks have disadvantage.',
        },
        {
          id: 'c2',
          name: 'prone',
          source: 'tactical',
          description: 'Knocked to ground; must crawl or spend movement to stand.',
        },
      ]}
      .penalties=${{
        drunk: 'Missed session! Kyra drank excessively at the tavern. Disadvantage on perception.',
        foolishness: 'Stand-in AI acts with overconfidence, ignoring danger.',
      }}
      .spellSlots=${{ 1: 1, 2: 0 }}
      .maxSpellSlots=${{ 1: 4, 2: 3 }}
      .preparedSpells=${['Cure Wounds', 'Bless', 'Spiritual Weapon']}
      .spellbook=${['Cure Wounds', 'Bless', 'Healing Word', 'Spiritual Weapon', 'Hold Person']}
    ></runefoble-character-sheet>
  `,
};

export const LeveledUpSpellcaster: Story = {
  render: () => html`
    <runefoble-character-sheet
      characterName="Gale of Waterdeep"
      characterClass="Wizard (Evocation) Lvl 5"
      .level=${5}
      .currentHp=${30}
      .maxHp=${30}
      .armorClass=${13}
      .initiative=${3}
      .speed=${30}
      .strength=${10}
      .equipment=${{
        main_hand: 'Arcane Staff',
        armor: 'Robes of the Archmagi',
        accessory: 'Ring of Spell Storing',
      }}
      .inventory=${[
        { item_id: 'w1', name: 'Arcane Staff', quantity: 1, weight_lbs: 4.0, slot: 'main_hand' },
        { item_id: 'w2', name: 'Robes of the Archmagi', quantity: 1, weight_lbs: 3.0, slot: 'armor' },
        { item_id: 'w3', name: 'Ring of Spell Storing', quantity: 1, weight_lbs: 0.1, slot: 'accessory' },
        { item_id: 'w4', name: 'Spell Component Pouch', quantity: 1, weight_lbs: 2.0 },
      ]}
      .spellSlots=${{ 1: 4, 2: 3, 3: 2 }}
      .maxSpellSlots=${{ 1: 4, 2: 3, 3: 2 }}
      .preparedSpells=${['Shield', 'Magic Missile', 'Misty Step', 'Fireball', 'Counterspell']}
      .spellbook=${[
        'Shield',
        'Magic Missile',
        'Mage Armor',
        'Detect Magic',
        'Misty Step',
        'Scorching Ray',
        'Fireball',
        'Counterspell',
        'Haste',
        'Fly',
      ]}
    ></runefoble-character-sheet>
  `,
};
