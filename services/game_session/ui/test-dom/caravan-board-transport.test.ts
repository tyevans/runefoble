/**
 * Caravan board over the shared transport (TASK-0759).
 * `<runefoble-caravan-board>` runs in headless Chromium. It posts to a live loopback upstream
 * through its `api-base`. The shell bearer comes from `<runefoble-story-auth-provider>`.
 * Nothing replaces `fetch`. The test reads the upstream log and the rendered banner, as a
 * player would. Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { commands } from 'vitest/browser';
import '@runefoble/ui-core/story-auth-provider';
import '../src/runefoble-caravan-board.ts';
import type { CaravanContractItem } from '../src/runefoble-caravan-types.ts';

interface Received { method: string; path: string; authorization: string | null; body: string }

const upstream = commands as unknown as {
  upstreamUrl(): Promise<string>;
  upstreamReply(status: number, body: unknown): Promise<void>;
  upstreamReset(): Promise<void>;
  upstreamRequests(): Promise<Received[]>;
};

const TOKEN = 'caravan-dom-token';
type Board = HTMLElement & { updateComplete: Promise<boolean>; contracts: CaravanContractItem[] };

function contract(status: CaravanContractItem['status']): CaravanContractItem {
  return {
    contract_id: 'contract-9',
    origin_outpost: 'Ironford',
    destination_outpost: 'Bastion Cross',
    cargo: { refined_iron: 20 },
    cargo_value: 600,
    route_risk_level: 'medium',
    transit_stages: 2,
    current_stage: 0,
    escort_collateral: 100,
    reward_gold: 300,
    reward_reputation: 20,
    status,
  } as CaravanContractItem;
}

async function mount(status: CaravanContractItem['status']): Promise<Board> {
  const provider = document.createElement('runefoble-story-auth-provider') as HTMLElement & { token: string };
  provider.token = TOKEN;
  const board = document.createElement('runefoble-caravan-board') as Board;
  board.setAttribute('api-base', `${await upstream.upstreamUrl()}/api/v1`);
  board.setAttribute('shared-world-id', 'world-ashen');
  board.setAttribute('campaign-id', 'camp-amber');
  board.setAttribute('party-name', 'The Amber Vanguard');
  board.contracts = [contract(status)];
  provider.append(board);
  document.body.append(provider);
  await board.updateComplete;
  return board;
}

async function clickCardButton(board: Board, label: string): Promise<void> {
  const card = board.shadowRoot?.querySelector('runefoble-caravan-contract-card') as HTMLElement & { updateComplete: Promise<boolean> };
  await card.updateComplete;
  const button = [...(card.shadowRoot?.querySelectorAll('button') ?? [])].find((b) => b.textContent?.includes(label));
  if (!button) throw new Error(`No button "${label}"`);
  button.click();
}

async function bannerText(board: Board): Promise<string> {
  const read = () => board.shadowRoot?.querySelector('.notification-banner span')?.textContent?.trim() ?? '';
  await expect.poll(read).not.toBe('');
  return read();
}

function statusBadge(board: Board): string {
  const card = board.shadowRoot?.querySelector('runefoble-caravan-contract-card');
  return card?.shadowRoot?.querySelector('.status-badge')?.textContent?.trim() ?? '';
}

beforeEach(() => upstream.upstreamReset());

afterEach(() => {
  document.querySelectorAll('runefoble-story-auth-provider').forEach((el) => el.remove());
});

describe('runefoble-caravan-board transport', () => {
  it('dispatches to the shared-world route with the shell bearer', async () => {
    await upstream.upstreamReply(200, {});
    const board = await mount('accepted');

    await clickCardButton(board, 'Dispatch');

    expect(await bannerText(board)).toBe('Caravan dispatched from Ironford!');
    const [request] = await upstream.upstreamRequests();
    expect(request.method).toBe('POST');
    expect(request.path).toBe('/api/v1/shared-worlds/world-ashen/caravans/contracts/contract-9/dispatch');
    expect(request.authorization).toBe(`Bearer ${TOKEN}`);
    expect(JSON.parse(request.body)).toEqual({ dispatched_by_campaign_id: 'camp-amber' });
  });

  it('shows the not-authorized text on a 403 and keeps the contract accepted', async () => {
    await upstream.upstreamReply(403, { detail: 'Forbidden' });
    const board = await mount('accepted');

    await clickCardButton(board, 'Dispatch');

    expect(await bannerText(board)).toBe('Dispatch failed: Your account is not authorized for this caravan action.');
    expect(statusBadge(board)).toBe('accepted');
  });

  it('shows the service-unavailable text on a 503', async () => {
    await upstream.upstreamReply(503, { detail: 'Caravan route service is unavailable.' });
    const board = await mount('in_transit');

    await clickCardButton(board, 'Fulfill');

    expect(await bannerText(board)).toBe('Fulfilment failed: Service unavailable: Caravan route service is unavailable.');
    expect(statusBadge(board)).toBe('in transit');
  });

  it('shows a refused accept as an error and does not claim the contract', async () => {
    await upstream.upstreamReply(403, { detail: 'Forbidden' });
    const board = await mount('open');
    let accepted = false;
    board.addEventListener('contract-accepted', () => { accepted = true; });

    await clickCardButton(board, 'Accept Escort Contract');

    expect(await bannerText(board)).toBe('Accept failed: Your account is not authorized for this caravan action.');
    expect(statusBadge(board)).toBe('open');
    expect(accepted).toBe(false);
  });
});
