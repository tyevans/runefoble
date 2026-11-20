/**
 * Session end in the App Shell (TASK-0953).
 *
 * A `session_ended` frame for the shell's own session moves the view to the recap and reloads
 * the committed chronicle. Another session's frame changes nothing. The `ended` status is final:
 * a status read that answers after the end cannot show the session as active again.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { applySessionStatus } from '../../src/app/session-data-loader.ts';
import { applySessionEndedFrame, type SessionEndHost } from '../../src/app/session-messages.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';

function fakeHost(overrides: Partial<SessionEndHost> = {}): SessionEndHost & { reloads: number } {
  const host = {
    sessionId: 'session-live',
    sessionStatus: 'active',
    isEndSessionConfirmOpen: true,
    reloads: 0,
    reloadRouteData() {
      host.reloads += 1;
    },
    ...overrides,
  };
  return host;
}

describe('applySessionEndedFrame', () => {
  it('shows the recap and reloads the chronicle for the shell session', () => {
    const host = fakeHost();

    const applied = applySessionEndedFrame(host, { type: 'session_ended', sessionId: 'session-live', status: 'ended' });

    assert.equal(applied, true);
    assert.equal(host.sessionStatus, 'ended');
    assert.equal(host.isEndSessionConfirmOpen, false);
    assert.equal(host.reloads, 1);
  });

  it('ignores a frame for another session', () => {
    const host = fakeHost();

    const applied = applySessionEndedFrame(host, { sessionId: 'session-other', status: 'ended' });

    assert.equal(applied, false);
    assert.equal(host.sessionStatus, 'active');
    assert.equal(host.reloads, 0);
  });

  it('ignores a frame that does not carry the ended status', () => {
    const host = fakeHost();

    const applied = applySessionEndedFrame(host, { sessionId: 'session-live', status: 'active' });

    assert.equal(applied, false);
    assert.equal(host.sessionStatus, 'active');
    assert.equal(host.reloads, 0);
  });
});

describe('applySessionStatus', () => {
  it('takes the owner status while the session is live', () => {
    const host = { sessionStatus: '' } as RunefobleApp;

    applySessionStatus(host, 'active');

    assert.equal(host.sessionStatus, 'active');
  });

  it('keeps ended after a status read that answers active', () => {
    const host = { sessionStatus: 'ended' } as RunefobleApp;

    applySessionStatus(host, 'active');

    assert.equal(host.sessionStatus, 'ended');
  });
});
