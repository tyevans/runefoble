import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-dm-trap-controls.ts';
import './runefoble-map-switcher.ts';

const meta: Meta = {
  title: 'BoardState/DMTrapControls',
  component: 'runefoble-dm-trap-controls',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleMaps = [
  { id: 'dungeon_lvl1', name: 'Catacombs of Despair - L1', cols: 15, rows: 15, spawnCoords: [2, 2] as [number, number] },
  { id: 'dungeon_lvl2', name: 'Sanctum of the Wyrm - L2', cols: 20, rows: 20, spawnCoords: [10, 15] as [number, number] },
  { id: 'cavern_depths', name: 'Underdark Chasm', cols: 25, rows: 25, spawnCoords: [4, 6] as [number, number] },
];

export const HiddenLayerActive: Story = {
  render: () => html`
    <div style="max-width: 420px; padding: 20px; background: #f4f4f4;">
      <runefoble-dm-trap-controls .layerVisible=${true} .selectedTrapType=${'pit_trap'}></runefoble-dm-trap-controls>
    </div>
  `,
};

export const HiddenLayerDisabled: Story = {
  render: () => html`
    <div style="max-width: 420px; padding: 20px; background: #f4f4f4;">
      <runefoble-dm-trap-controls .layerVisible=${false}></runefoble-dm-trap-controls>
    </div>
  `,
};

export const TrapArmingPalette: Story = {
  render: () => html`
    <div style="max-width: 420px; padding: 20px; background: #f4f4f4;">
      <runefoble-dm-trap-controls
        .selectedTrapType=${'glyph'}
        .triggerType=${'proximity'}
        .proximityRadius=${3}
        .damageDice=${'5d8'}
        .dcDetection=${18}
      ></runefoble-dm-trap-controls>
    </div>
  `,
};

export const DangerZonePreview: Story = {
  render: () => html`
    <div style="max-width: 420px; padding: 20px; background: #f4f4f4;">
      <runefoble-dm-trap-controls
        .selectedTrapType=${'tripwire'}
        .triggerType=${'touch'}
        .proximityRadius=${1}
        .damageDice=${'1d6'}
        .dcDetection=${12}
      ></runefoble-dm-trap-controls>
    </div>
  `,
};

export const MultiMapSwitcherModal: Story = {
  render: () => html`
    <div style="max-width: 600px; padding: 20px; position: relative; min-height: 400px;">
      <runefoble-map-switcher
        .open=${true}
        .currentMapId=${'dungeon_lvl1'}
        .maps=${sampleMaps}
      ></runefoble-map-switcher>
    </div>
  `,
};
