import '@runefoble/ui-core/story-auth-provider';
import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-dm-trap-controls.ts';

const meta: Meta = {
  title: 'BoardState/DMTrapControls',
  component: 'runefoble-dm-trap-controls',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

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

/** Replaces window.fetch for one story. Records each call and returns a fixed response. */
function stubFetchForStory(status: number, body: unknown) {
  const calls: { url: string; method: string | undefined; body: unknown; auth: string | null }[] = [];
  const original = window.fetch;
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({
      url: String(input),
      method: init?.method,
      body: JSON.parse(String(init?.body)),
      auth: new Headers(init?.headers).get('Authorization'),
    });
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
      <runefoble-story-auth-provider token="story-token">
        <runefoble-dm-trap-controls
          .boardId=${'board-42'}
          .targetX=${4}
          .targetY=${5}
        ></runefoble-dm-trap-controls>
      </runefoble-story-auth-provider>
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
      if (call.url !== '/api/v1/boards/board-42/traps') throw new Error(`Wrong URL: ${call.url}`);
      if (call.method !== 'POST') throw new Error(`Wrong method: ${call.method}`);
      if (call.auth !== 'Bearer story-token') throw new Error(`Missing bearer: ${call.auth}`);
      const body = call.body as Record<string, unknown>;
      if (body.x !== 4 || body.y !== 5 || body.trap_type !== 'pit_trap') throw new Error('Wrong trap body');
    } finally {
      stub.restore();
    }
  },
};
