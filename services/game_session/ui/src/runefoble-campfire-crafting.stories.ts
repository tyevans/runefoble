import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campfire-crafting.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCampfireCrafting',
  component: 'runefoble-campfire-crafting',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultCampfireAndLaboratory: Story = {
  render: () => html`
    <runefoble-campfire-crafting
      session-id="session-campfire-01"
      campaign-id="campaign-shadow-valley"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      rest-type="long"
      storytelling-prompt="The embers cast long shadows across the clearing. Evelyn asks Bram what inspired his clockwork devices."
    ></runefoble-campfire-crafting>
  `,
};

export const ActiveCrucibleWithReagents: Story = {
  render: () => html`
    <runefoble-campfire-crafting
      session-id="session-campfire-02"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      .selectedReagents=${['Glowmoss Extract', 'Volcano Ash']}
      selectedCatalyst="purified_water"
    ></runefoble-campfire-crafting>
  `,
};

export const CraftingSuccessOutcome: Story = {
  render: () => html`
    <runefoble-campfire-crafting
      session-id="session-campfire-03"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      .selectedReagents=${['Glowmoss Extract', 'Volcano Ash']}
      .lastOutcome=${{
        outcome: 'success',
        item_name: 'Radiant Smoke Pellet',
        message: 'Synthesized 1x Radiant Smoke Pellet! Illumination and smoke burst ready.',
        tags: ['consumable', 'radiant', 'obscurement', 'aoe'],
      }}
    ></runefoble-campfire-crafting>
  `,
};

export const VolatileMishapAlert: Story = {
  render: () => html`
    <runefoble-campfire-crafting
      session-id="session-campfire-04"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      .selectedReagents=${['Volcano Ash', 'Nightshade Berry']}
      selectedCatalyst="none"
      .lastOutcome=${{
        outcome: 'mishap',
        message: 'Volatile Reaction! Crucible exploded with caustic purple fumes. Crafter takes 4 damage.',
      }}
    ></runefoble-campfire-crafting>
  `,
};

export const FortifiedStrongholdBoons: Story = {
  render: () => html`
    <runefoble-campfire-crafting
      session-id="session-campfire-05"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      .strongholdFacilities=${{
        watchtower: 2,
        herbal_rack: 2,
        arcane_forge: 1,
      }}
      .activeBoons=${[
        'Campfire Camaraderie (+1 Morale to Initiative)',
        'Vigilant Sentry (+2 Passive Perception)',
        'Vantage Scouting (Advantage on Initiative)',
        'Restorative Brews (+1d4 Rest Healing)',
        'Alchemical Affinity (+15% Crafting Stability)',
        'Honed Blades (+1 Weapon Damage on first encounter)',
      ]}
    ></runefoble-campfire-crafting>
  `,
};
