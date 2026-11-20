/**
 * App Shell host of the DM whisper bar: the veto (TASK-0949).
 *
 * The bar sends `action-vetoed`. The shell posts the gateway veto route and reports the reply to
 * the bar that sent the event. The gateway is faked at the fetch boundary.
 * Governing ADRs: ADR-0002, ADR-0013, ADR-0015.
 */

import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { handleActionVetoed, whisperBarProps } from '../src/app/whisper-bar-actions.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

/** Stands in for the bar element: it records what the shell reports to it. */
class BarDouble extends EventTarget {
  vetoed: string[] = [];
  errors: string[] = [];
  markActionVetoed(actionId: string): void { this.vetoed.push(actionId); }
  showActionError(message: string): void { this.errors.push(message); }
}

const DETAIL = { actionId: 'act-1', reason: 'DM one-click veto', sessionId: 'sess-1', campaignId: 'camp-1' };

async function veto(bar: BarDouble): Promise<void> {
  let handled: Promise<void> = Promise.resolve();
  bar.addEventListener('action-vetoed', (e) => { handled = handleActionVetoed(e); });
  bar.dispatchEvent(new CustomEvent('action-vetoed', { detail: DETAIL }));
  await handled;
}

describe('whisper bar veto host', () => {
  let gateway: FakeGateway;
  afterEach(() => gateway?.restore());

  it('posts the veto route and marks the action as vetoed on a 200 reply', async () => {
    gateway = installFakeGateway({ 'POST /api/v1/watcher/veto': { body: { status: 'vetoed', action_id: 'act-1' } } });
    const bar = new BarDouble();

    await veto(bar);

    assert.deepEqual(gateway.calls.map((c) => [c.method, c.path, c.body]), [
      ['POST', '/api/v1/watcher/veto', { session_id: 'sess-1', campaign_id: 'camp-1', action_id: 'act-1', reason: 'DM one-click veto' }],
    ]);
    assert.deepEqual(bar.vetoed, ['act-1']);
    assert.deepEqual(bar.errors, []);
  });

  it('shows the owner reason and does not mark the action when the veto is refused', async () => {
    gateway = installFakeGateway({ 'POST /api/v1/watcher/veto': { status: 403, body: { detail: 'Forbidden: DM only' } } });
    const bar = new BarDouble();

    await veto(bar);

    assert.deepEqual(bar.vetoed, []);
    assert.equal(bar.errors.length, 1);
    assert.match(bar.errors[0], /^Veto failed: .*Forbidden/);
  });

  it('gives the bar the ids of the open session', () => {
    assert.deepEqual(whisperBarProps('sess-1', 'camp-1'), { 'default-dm-whisper-bar': { sessionId: 'sess-1', campaignId: 'camp-1' } });
  });
});
