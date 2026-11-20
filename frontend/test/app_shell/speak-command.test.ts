/**
 * The typed command bar in the App Shell (TASK-0945).
 *
 * The shell posts the `speak-command` body to the gateway speak-and-act route, and sets the
 * bar status from the reply. The shell finds the caller's token by its character. The gateway
 * is the only fake (Hard Invariant 7). ADR-0013, ADR-0022 (c).
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import type { CommandBarStatus, SpeakCommandBody } from '@runefoble/the-watcher-ui';
import { handleSpeakCommand } from '../../src/vtt-mesh-handlers.ts';
import { speakerTokenCell } from '../../src/app/command-bar-context.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';

const ROUTE = 'POST /api/v1/watcher/speak-and-act';

const BODY: SpeakCommandBody = {
  speaker_id: 'char-valeros',
  speaker_name: 'Valeros the Bold',
  transcript: 'move 2 squares west',
  session_id: 'session-tomb-14',
  campaign_id: 'campaign-4',
  token_id: 'tok-valeros',
  from_x: 4,
  from_y: 2,
  grid_cols: 10,
  grid_rows: 10,
};

function host() {
  return { commandStatus: { kind: 'idle' } as CommandBarStatus };
}

function command(): CustomEvent<SpeakCommandBody> {
  return new CustomEvent('speak-command', { detail: BODY });
}

describe('handleSpeakCommand', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('posts the command body as sent and shows the Watcher reply', async () => {
    gateway = installFakeGateway({
      [ROUTE]: { body: { action_type: 'move', watcher_reply: 'Valeros the Bold moves 2 squares west.', parameters: { dx: -2 } } },
    });
    const h = host();

    await handleSpeakCommand(h, command());

    assert.deepEqual(gateway.calls.map((c) => `${c.method} ${c.path}`), [ROUTE]);
    assert.deepEqual(gateway.calls[0].body, BODY);
    assert.deepEqual(h.commandStatus, { kind: 'reply', text: 'Valeros the Bold moves 2 squares west.' });
  });

  it('shows "Not understood." when The Watcher does not parse the command', async () => {
    gateway = installFakeGateway({ [ROUTE]: { body: { action_type: 'narrative', watcher_reply: 'Not understood.' } } });
    const h = host();

    await handleSpeakCommand(h, command());

    assert.deepEqual(h.commandStatus, { kind: 'reply', text: 'Not understood.' });
  });

  it('shows the status and the detail of a refused or failed call', async () => {
    gateway = installFakeGateway({ [ROUTE]: { status: 503, body: { detail: 'Upstream service is unavailable' } } });
    const h = host();

    await handleSpeakCommand(h, command());

    assert.deepEqual(h.commandStatus, { kind: 'error', text: 'HTTP 503: Upstream service is unavailable' });
  });

  it('shows an error for a 2xx reply without watcher_reply', async () => {
    gateway = installFakeGateway({ [ROUTE]: { body: { action_type: 'move' } } });
    const h = host();

    await handleSpeakCommand(h, command());

    assert.equal(h.commandStatus.kind, 'error');
  });
});

describe('speakerTokenCell', () => {
  const tokens = [
    { id: 'tok-ghoul', name: 'Ghoul', x: 7, y: 6 },
    { id: 'tok-valeros', name: 'Valeros the Bold', x: 3, y: 0, characterId: 'char-valeros' },
  ];

  it('gives the token and the shown cell of the character', () => {
    assert.deepEqual(speakerTokenCell(tokens, 'char-valeros'), { tokenId: 'tok-valeros', fromX: 3, fromY: 0 });
  });

  it('gives no token for a character without a token, and for no character', () => {
    assert.deepEqual(speakerTokenCell(tokens, 'char-sarah'), { tokenId: null, fromX: null, fromY: null });
    assert.deepEqual(speakerTokenCell(tokens, null), { tokenId: null, fromX: null, fromY: null });
  });
});
