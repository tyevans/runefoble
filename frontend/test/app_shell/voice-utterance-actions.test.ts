/**
 * App Shell side of Push to Talk (TASK-0946).
 *
 * `<runefoble-voice-controls>` emits `voice-utterance` with the WAV. The App Shell posts it to the
 * gateway transcribe route with the speaker, the session and the board origin, and puts the reply
 * on `voiceUtterance`. A failed upload is shown. No transcript is shown that the route did not
 * return. The gateway is faked at the fetch boundary only.
 * Governing ADRs: ADR-0013, ADR-0015.
 */

import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { IDLE_VOICE_UTTERANCE, sendVoiceUtterance } from '../../src/app/voice-utterance-actions.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';

const ROUTE = 'POST /api/v1/voice/transcribe';
const ORIGIN = { token_id: 'tok-valeros', from_x: 2, from_y: 3, grid_cols: 12, grid_rows: 10 };

function host(overrides: Record<string, unknown> = {}) {
  return {
    sessionId: 'sess-1',
    campaignId: 'camp-1',
    currentUserId: 'user-valeros',
    activeCharacter: { id: 'char-valeros', name: 'Valeros' },
    voiceUtterance: IDLE_VOICE_UTTERANCE,
    ...overrides,
  } as unknown as RunefobleApp;
}

let gateway: FakeGateway | null = null;
afterEach(() => {
  gateway?.restore();
  gateway = null;
});

describe('Push to Talk upload in the App Shell', () => {
  it('posts the audio, the speaker, the session and the board origin', async () => {
    gateway = installFakeGateway({ [ROUTE]: { body: { transcript: 'move north', source: 'audio', watcher_error: null } } });
    const app = host();

    await sendVoiceUtterance(app, 'UklGRg==', ORIGIN);

    assert.equal(gateway.calls.length, 1);
    assert.deepEqual(gateway.calls[0].body, {
      speaker_id: 'user-valeros',
      speaker_name: 'Valeros',
      session_id: 'sess-1',
      campaign_id: 'camp-1',
      audio_base64: 'UklGRg==',
      ...ORIGIN,
    });
    assert.deepEqual(app.voiceUtterance, { sending: false, transcript: 'move north', watcherError: '', uploadError: '' });
  });

  it('sends no origin fields when the speaker has no board token', async () => {
    gateway = installFakeGateway({ [ROUTE]: { body: { transcript: 'I look around', source: 'audio' } } });

    await sendVoiceUtterance(host(), 'UklGRg==', null);

    const body = gateway.calls[0].body as Record<string, unknown>;
    assert.equal('token_id' in body, false);
    assert.equal('from_x' in body, false);
  });

  it('shows the Watcher error next to the transcript', async () => {
    gateway = installFakeGateway({ [ROUTE]: { body: { transcript: 'move north', source: 'audio', watcher_error: 'The Watcher answered 422' } } });
    const app = host();

    await sendVoiceUtterance(app, 'UklGRg==', ORIGIN);

    assert.equal(app.voiceUtterance.transcript, 'move north');
    assert.equal(app.voiceUtterance.watcherError, 'The Watcher answered 422');
  });

  it('shows a refused upload with its status and detail, and no transcript', async () => {
    gateway = installFakeGateway({ [ROUTE]: { status: 503, body: { error: 'speech_engine_unavailable', message: 'The speech engine is unavailable.' } } });
    const app = host({ voiceUtterance: { ...IDLE_VOICE_UTTERANCE, transcript: 'an old transcript' } });

    await sendVoiceUtterance(app, 'UklGRg==', ORIGIN);

    assert.equal(app.voiceUtterance.transcript, '');
    assert.equal(app.voiceUtterance.sending, false);
    assert.equal(app.voiceUtterance.uploadError, 'Push to Talk failed (503): The speech engine is unavailable.');
  });

  it('says that no words were heard when the engine returns an empty transcript', async () => {
    gateway = installFakeGateway({ [ROUTE]: { body: { transcript: '', source: 'audio' } } });
    const app = host();

    await sendVoiceUtterance(app, 'UklGRg==', ORIGIN);

    assert.equal(app.voiceUtterance.transcript, '');
    assert.match(app.voiceUtterance.uploadError, /No words were heard/);
  });

  it('treats a reply without a transcript as a failed upload', async () => {
    gateway = installFakeGateway({ [ROUTE]: { body: { source: 'audio' } } });
    const app = host();

    await sendVoiceUtterance(app, 'UklGRg==', ORIGIN);

    assert.equal(app.voiceUtterance.transcript, '');
    assert.match(app.voiceUtterance.uploadError, /^Push to Talk failed \(502\)/);
  });

  it('sends nothing while the session is not known', async () => {
    gateway = installFakeGateway({});
    const app = host({ sessionId: '' });

    await sendVoiceUtterance(app, 'UklGRg==', ORIGIN);

    assert.equal(gateway.calls.length, 0);
    assert.match(app.voiceUtterance.uploadError, /session is not known/);
  });
});
