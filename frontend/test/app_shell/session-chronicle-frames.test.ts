/**
 * App Shell side of the live chronicle line (`chronicle_entry` session frame).
 *
 * The gateway sends a `chronicle_entry` frame when game_session records a chronicle line, for
 * example a board token move. The shell adds the line to the Watcher feed once. A line that the
 * feed already holds (from the chronicle read or an earlier frame) is not added again.
 * Governing ADRs: ADR-0011, ADR-0013, ADR-0015.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { handleSessionMessage } from '../../src/app/session-messages.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';

function host(): RunefobleApp {
  return { events: [] } as unknown as RunefobleApp;
}

const ENTRY = {
  event_id: 'evt-move-1',
  kind: 'token_moved',
  occurred_at: '2026-11-19T10:00:00Z',
  speaker: 'Valeros the Bold',
  text: 'Valeros the Bold moved to (3, 3)',
  action_type: 'board_move',
  penalties: [],
};

describe('live chronicle lines in the App Shell', () => {
  it('adds a token move line to the Watcher feed', () => {
    const app = host();
    handleSessionMessage(app, { type: 'chronicle_entry', sessionId: 'sess-1', entry: ENTRY });
    assert.equal(app.events.length, 1);
    const [line] = app.events;
    assert.equal(line.id, 'evt-move-1');
    assert.equal(line.speaker, 'Valeros the Bold');
    assert.equal(line.text, 'Valeros the Bold moved to (3, 3)');
    assert.equal(line.actionType, 'board_move');
    assert.equal(line.source, 'player');
  });

  it('adds a line that the feed already holds only once', () => {
    const app = host();
    handleSessionMessage(app, { type: 'chronicle_entry', sessionId: 'sess-1', entry: ENTRY });
    handleSessionMessage(app, { type: 'chronicle_entry', sessionId: 'sess-1', entry: ENTRY });
    assert.equal(app.events.length, 1);
  });
});
