/**
 * Unit tests for the whisper bar action rules. TASK-0838.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { whisperAction } from '../src/whisper-actions.ts';

describe('whisperAction', () => {
  it('offers Send on an audience narration the DM has not sent', () => {
    assert.equal(
      whisperAction({ whisper_type: 'audience_narration', metadata: { dispatched: false } }),
      'send',
    );
    assert.equal(whisperAction({ whisper_type: 'audience_narration' }), 'send');
  });

  it('shows a sent badge, not Send, once the narration reached the table', () => {
    assert.equal(
      whisperAction({ whisper_type: 'audience_narration', metadata: { dispatched: true } }),
      'sent',
    );
  });

  it('shows narration_unavailable as a notice and never as a Send action', () => {
    assert.equal(
      whisperAction({
        whisper_type: 'narration_unavailable',
        metadata: { reason: 'The inference worker did not return narration.' },
      }),
      'notice',
    );
  });

  it('leaves the other whisper types without an extra action', () => {
    assert.equal(whisperAction({ whisper_type: 'atmospheric_hint' }), 'none');
    assert.equal(whisperAction({ whisper_type: 'monster_tactics' }), 'none');
    assert.equal(whisperAction({ whisper_type: 'passive_perception' }), 'none');
  });
});
