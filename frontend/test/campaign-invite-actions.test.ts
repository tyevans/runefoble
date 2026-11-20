/**
 * Invite link state in the App Shell (TASK-0973). The shell clears the link field while a
 * Generate request is out, and sets it only from the reply. A refused request leaves no link.
 * The gateway is faked at the fetch boundary. Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createInviteFromEvent } from '../src/app/campaign-actions.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const CAMPAIGN_ID = 'camp-9';
const OLD_TOKEN = 'tok-old-11';
const NEW_TOKEN = 'tok-new-22';
const OLD_LINK = `https://runefoble.test/#/join/${OLD_TOKEN}`;
const NEW_LINK = `https://runefoble.test/#/join/${NEW_TOKEN}`;
const INVITE_ROUTE = `POST /api/v1/campaigns/${CAMPAIGN_ID}/invites`;

interface Observation { inviteUrl: string; pending: boolean }

function hostWith(inviteUrl: string) {
  const toasts: string[] = [];
  return {
    campaignId: CAMPAIGN_ID,
    inviteUrl,
    inviteRequestPending: false,
    toasts,
    showToast(message: string) { toasts.push(message); },
  };
}

function createInviteEvent(): CustomEvent {
  return new CustomEvent('create-invite', { detail: { campaignId: CAMPAIGN_ID, role: 'player' } });
}

describe('createInviteFromEvent link state (TASK-0973)', () => {
  let gateway: FakeGateway | null = null;
  let previousWindow: unknown;

  beforeEach(() => {
    previousWindow = (globalThis as { window?: unknown }).window;
    (globalThis as { window?: unknown }).window = { location: { origin: 'https://runefoble.test' } };
  });

  afterEach(() => {
    gateway?.restore();
    gateway = null;
    (globalThis as { window?: unknown }).window = previousWindow;
  });

  it('clears the old link and marks the request pending while the request is out', async () => {
    const seen: Observation[] = [];
    const host = hostWith(OLD_LINK);
    gateway = installFakeGateway({
      [INVITE_ROUTE]: () => {
        seen.push({ inviteUrl: host.inviteUrl, pending: host.inviteRequestPending });
        return { status: 201, body: { token: NEW_TOKEN, campaign_id: CAMPAIGN_ID, role: 'player', invite_url: `/#/join/${NEW_TOKEN}`, created_at: '2026-11-19T00:00:00Z' } };
      },
    });

    await createInviteFromEvent(host as any, createInviteEvent());

    assert.deepEqual(seen, [{ inviteUrl: '', pending: true }]);
    assert.equal(host.inviteUrl, NEW_LINK);
    assert.equal(host.inviteRequestPending, false);
  });

  it('leaves no link after a refused request, and never the old link', async () => {
    const host = hostWith(OLD_LINK);
    gateway = installFakeGateway({
      [INVITE_ROUTE]: { status: 503, body: { detail: 'Invite service is unavailable.' } },
    });

    await createInviteFromEvent(host as any, createInviteEvent());

    assert.equal(host.inviteUrl, '');
    assert.equal(host.inviteRequestPending, false);
    assert.deepEqual(host.toasts, ['Invite not created. Invite service is unavailable.']);
  });

  it('keeps the invite token out of the messages it shows', async () => {
    const host = hostWith('');
    gateway = installFakeGateway({
      [INVITE_ROUTE]: { status: 500, body: { detail: 'Invite service failed.' } },
    });

    await createInviteFromEvent(host as any, createInviteEvent());

    for (const message of host.toasts) {
      assert.ok(!message.includes(OLD_TOKEN) && !message.includes(NEW_TOKEN));
    }
  });
});
