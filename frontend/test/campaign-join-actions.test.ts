/**
 * The join view state (ADR-0023, TASK-0950). The account and join calls run at the fetch
 * boundary through the fake gateway. The token never appears in a state message.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  IDLE_JOIN_STATE,
  accountFailureMessage,
  joinCampaignFromView,
  joinStateFor,
  requestInviteAccount,
  resolveJoinPhase,
  type JoinViewState,
} from '../src/app/campaign-join-actions.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const TOKEN = 'tok-secret-77';
let gateway: FakeGateway | null = null;

afterEach(() => {
  gateway?.restore();
  gateway = null;
});

function hostWith(state: JoinViewState = IDLE_JOIN_STATE): any {
  return { joinState: state, routeParams: { token: TOKEN } };
}

describe('resolveJoinPhase', () => {
  it('shows the account form to a signed-out visitor and the join button to a signed-in person', () => {
    assert.equal(resolveJoinPhase(joinStateFor(hostWith(), TOKEN), false), 'account-form');
    assert.equal(resolveJoinPhase(joinStateFor(hostWith(), TOKEN), true), 'join-ready');
  });

  it('never shows the account form to a signed-in person, and never the join button to a signed-out one', () => {
    const accepted: JoinViewState = { ...IDLE_JOIN_STATE, token: TOKEN, phase: 'account-accepted' };
    assert.equal(resolveJoinPhase(accepted, true), 'join-ready');
    const ready: JoinViewState = { ...IDLE_JOIN_STATE, token: TOKEN, phase: 'join-ready' };
    assert.equal(resolveJoinPhase(ready, false), 'account-form');
  });

  it('keeps the state of the same token only', () => {
    const joining: JoinViewState = { ...IDLE_JOIN_STATE, token: 'other', phase: 'joining' };
    assert.equal(joinStateFor(hostWith(joining), TOKEN).phase, 'idle');
  });
});

describe('accountFailureMessage', () => {
  it('maps each refusal to a fixed text that does not repeat the input', () => {
    for (const status of [404, 410, 422, 429, 503, 500]) {
      const message = accountFailureMessage(status);
      assert.ok(message.length > 0);
      assert.ok(!message.includes(TOKEN));
    }
    assert.equal(accountFailureMessage(410), 'This invite link has expired or has no uses left.');
  });
});

describe('requestInviteAccount', () => {
  it('sends the invite in the body without a bearer and moves to the e-mail phase', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/campaigns/invites/accounts': { status: 202, body: { status: 'accepted', message: 'Check your e-mail.' } },
    });
    const host = hostWith();

    await requestInviteAccount(host, { inviteToken: TOKEN, email: 'new@example.test', displayName: 'New' });

    assert.equal(gateway.calls.length, 1);
    assert.deepEqual(gateway.calls[0].body, { invite_token: TOKEN, email: 'new@example.test', display_name: 'New' });
    assert.equal(host.joinState.phase, 'account-accepted');
    assert.equal(host.joinState.message, '');
  });

  it('shows the fixed text for a refused invite and keeps the token out of the state', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/campaigns/invites/accounts': { status: 410, body: { detail: 'invite_expired' } },
    });
    const host = hostWith();

    await requestInviteAccount(host, { inviteToken: TOKEN, email: 'x@example.test', displayName: 'X' });

    assert.equal(host.joinState.phase, 'account-refused');
    assert.equal(host.joinState.message, 'This invite link has expired or has no uses left.');
    assert.ok(!host.joinState.message.includes(TOKEN));
  });
});

describe('joinCampaignFromView', () => {
  it('joins with the token, then opens the campaign', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/campaigns/join': { status: 200, body: { status: 'joined', campaign_id: 'camp-7', user_id: 'u1', role: 'player', zanzibar_relation: 'player' } },
    });
    const host = hostWith();

    await joinCampaignFromView(host, TOKEN);

    assert.deepEqual(gateway.calls[0].body, { invite_token: TOKEN });
    assert.equal(host.joinState.phase, 'joined');
    assert.equal(host.joinState.campaignId, 'camp-7');
    assert.equal(host.joinState.memberRole, 'player');
  });

  it('shows the server refusal text when the join is refused', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/campaigns/join': { status: 404, body: { detail: 'Invite not found' } },
    });
    const host = hostWith();

    await joinCampaignFromView(host, TOKEN);

    assert.equal(host.joinState.phase, 'join-refused');
    assert.equal(host.joinState.message, 'Invite not found');
  });
});
