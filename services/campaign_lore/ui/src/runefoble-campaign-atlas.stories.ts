import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-atlas.ts';
import type { AtlasPin, AtlasTerritory, CodexEntry } from './runefoble-campaign-atlas.ts';

const meta: Meta = {
  title: 'CampaignLore/RunefobleCampaignAtlas',
  component: 'runefoble-campaign-atlas',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleTerritories: AtlasTerritory[] = [
  {
    territory_id: 'terr-1',
    name: 'Silverkeep Garrison',
    layer: 'continental',
    polygon_coordinates: [
      [150, 150],
      [450, 150],
      [450, 450],
      [150, 450],
    ],
    owner_faction: 'Silverguard Alliance',
    is_contested: false,
    era: 'Session 12: Liberation',
    metadata: { banner_color: '#4361ee' },
  },
  {
    territory_id: 'terr-2',
    name: 'Obsidian Borderlands',
    layer: 'continental',
    polygon_coordinates: [
      [450, 200],
      [750, 200],
      [700, 500],
      [450, 450],
    ],
    owner_faction: 'Disputed',
    is_contested: true,
    era: 'Age of Rebirth',
    metadata: { banner_color: '#d90429' },
  },
];

const samplePins: AtlasPin[] = [
  {
    pin_id: 'pin-1',
    title: 'Garrison Fortress Breach',
    layer: 'continental',
    coordinates: { x: 300, y: 300 },
    description: 'Where the party breached the western gates.',
    era: 'Session 12',
  },
  {
    pin_id: 'pin-2',
    title: 'Sunken Vault of Runes',
    layer: 'continental',
    coordinates: { x: 600, y: 350 },
    description: 'Ancient subterranean laboratory discovered.',
    era: 'Session 14',
  },
];

const sampleCodex: CodexEntry[] = [
  {
    entry_id: 'codex-1',
    title: 'Observations on the Obsidian Veil',
    content: 'Cabal operatives have established shadow conduits beneath the garrison.',
    privacy: 'private',
    author_id: 'rowan',
    linked_entities: [{ id: 'ent-1', name: 'Order of the Obsidian Veil', entity_type: 'faction' }],
  },
  {
    entry_id: 'codex-2',
    title: 'Silverkeep Defense Log',
    content: 'Allied forces reinforced the perimeter following the siege.',
    privacy: 'party_shared',
    author_id: 'valeros',
    linked_entities: [{ id: 'ent-2', name: 'Silverkeep Garrison', entity_type: 'location' }],
  },
];

export const ContinentalView: Story = {
  render: () => html`
    <runefoble-campaign-atlas
      campaignId="demo-camp-1"
      activeLayer="continental"
      .territories=${sampleTerritories}
      .pins=${samplePins}
      .codexEntries=${sampleCodex}
      .isDM=${true}
    ></runefoble-campaign-atlas>
  `,
};

export const ContestedTerritories: Story = {
  render: () => html`
    <runefoble-campaign-atlas
      campaignId="demo-camp-2"
      activeLayer="continental"
      .territories=${sampleTerritories}
      .pins=${samplePins}
      .codexEntries=${sampleCodex}
      .isDM=${false}
    ></runefoble-campaign-atlas>
  `,
};
