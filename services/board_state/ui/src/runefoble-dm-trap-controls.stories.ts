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
        .boardId=${'board-42'}
      ></runefoble-map-switcher>
    </div>
  `,
};

export const TeleportPostsSwitchMapRoute: Story = {
  render: () => html`
    <div style="max-width: 600px; padding: 20px; position: relative; min-height: 400px;">
      <runefoble-map-switcher
        .open=${true}
        .currentMapId=${'dungeon_lvl1'}
        .maps=${sampleMaps}
        .boardId=${'board-42'}
        .campaignId=${'camp-7'}
      ></runefoble-map-switcher>
    </div>
  `,
  play: async ({ canvasElement }) => {
    const stub = stubFetchForStory(200, {
      board_id: 'board-42', new_map_id: 'dungeon_lvl2', cols: 20, rows: 20,
      teleported_tokens: { valeros: [10, 15] }, status: 'switched',
    });
    try {
      const el = canvasElement.querySelector('runefoble-map-switcher') as HTMLElement;
      const buttons = el.shadowRoot?.querySelectorAll('.teleport-btn') ?? [];
      (buttons[1] as HTMLButtonElement).click();
      await waitForCall(stub.calls);
      const call = stub.calls[0];
      if (!call) throw new Error('No request sent to the switch-map route');
      if (call.url !== '/api/v1/boards/board-42/switch-map?campaign_id=camp-7') throw new Error(`Wrong URL: ${call.url}`);
      const body = call.body as Record<string, unknown>;
      if (body.new_map_id !== 'dungeon_lvl2' || body.cols !== 20) throw new Error('Wrong switch-map body');
    } finally {
      stub.restore();
    }
  },
};

/** Replaces window.fetch for one story. Records each call and returns a fixed response. */
function stubFetchForStory(status: number, body: unknown) {
  const calls: { url: string; method: string | undefined; body: unknown }[] = [];
  const original = window.fetch;
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), method: init?.method, body: JSON.parse(String(init?.body)) });
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  };
  return { calls, restore: () => { window.fetch = original; } };
}

async function waitForCall(calls: unknown[]): Promise<void> {
  for (let i = 0; i < 50 && calls.length === 0; i++) {
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
}

export const ArmTrapPostsToTrapsRoute: Story = {
  render: () => html`
    <div style="max-width: 420px; padding: 20px; background: #f4f4f4;">
      <runefoble-dm-trap-controls
        .boardId=${'board-42'}
        .campaignId=${'camp-7'}
        .targetX=${4}
        .targetY=${5}
      ></runefoble-dm-trap-controls>
    </div>
  `,
  play: async ({ canvasElement }) => {
    const stub = stubFetchForStory(201, { trap_id: 'trap-1', name: 'Spike Pit', is_armed: true });
    try {
      const el = canvasElement.querySelector('runefoble-dm-trap-controls') as HTMLElement;
      (el.shadowRoot?.querySelector('.btn-hud.primary') as HTMLButtonElement).click();
      await waitForCall(stub.calls);
      const call = stub.calls[0];
      if (!call) throw new Error('No request sent to the traps route');
      if (call.url !== '/api/v1/boards/board-42/traps?campaign_id=camp-7') throw new Error(`Wrong URL: ${call.url}`);
      if (call.method !== 'POST') throw new Error(`Wrong method: ${call.method}`);
      const body = call.body as Record<string, unknown>;
      if (body.x !== 4 || body.y !== 5 || body.trap_type !== 'pit_trap') throw new Error('Wrong trap body');
    } finally {
      stub.restore();
    }
  },
};
