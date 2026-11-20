/**
 * Unit tests for the typed command body (TASK-0945).
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildSpeakCommandBody, hasTokenCell, type CommandBarContext } from '../src/command-bar-body.ts';

const CONTEXT: CommandBarContext = {
  sessionId: 'session-tomb-14',
  campaignId: 'campaign-4',
  speakerId: 'char-valeros',
  speakerName: 'Valeros the Bold',
  tokenId: 'tok-valeros',
  fromX: 4,
  fromY: 2,
  gridCols: 10,
  gridRows: 8,
};

describe('buildSpeakCommandBody', () => {
  it('sends the speaker, the session, the token cell and the board size with the transcript', () => {
    assert.deepEqual(buildSpeakCommandBody(CONTEXT, '  move 2 squares west '), {
      speaker_id: 'char-valeros',
      speaker_name: 'Valeros the Bold',
      transcript: 'move 2 squares west',
      session_id: 'session-tomb-14',
      campaign_id: 'campaign-4',
      token_id: 'tok-valeros',
      from_x: 4,
      from_y: 2,
      grid_cols: 10,
      grid_rows: 8,
    });
  });

  it('sends a token at cell (0, 0) with its cell', () => {
    const body = buildSpeakCommandBody({ ...CONTEXT, fromX: 0, fromY: 0 }, 'move north');
    assert.equal(body?.from_x, 0);
    assert.equal(body?.from_y, 0);
  });

  it('builds no body for a blank transcript', () => {
    assert.equal(buildSpeakCommandBody(CONTEXT, '   '), null);
  });

  it('builds no body without the token or its cell', () => {
    assert.equal(buildSpeakCommandBody({ ...CONTEXT, tokenId: null }, 'move north'), null);
    assert.equal(buildSpeakCommandBody({ ...CONTEXT, fromX: null }, 'move north'), null);
    assert.equal(buildSpeakCommandBody({ ...CONTEXT, fromY: null }, 'move north'), null);
    assert.equal(hasTokenCell({ ...CONTEXT, fromX: 1.5 }), false);
  });
});
