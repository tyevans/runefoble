/**
 * Transport tests of the DM whisper bar client (TASK-0949).
 *
 * Each call goes to a real HTTP server on the loopback interface. Nothing replaces `fetch`.
 * The tests read what the server received and what the call resolved or rejected with.
 */

import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { HttpError } from '@runefoble/ui-core';
import { startLoopbackUpstream, type LoopbackUpstream } from '@runefoble/ui-core/testing/loopback-upstream';
import { fetchPendingActions, fetchWhispers, generateWhispers, openAction } from '../src/whisper-bar-api.ts';

const SCOPE = { sessionId: 'sess-1', campaignId: 'camp-1' };
const auth = { authHeaders: async () => ({ Authorization: 'Bearer dm-token' }) };

let upstream: LoopbackUpstream;
const opts = () => ({ apiBase: upstream.url, auth });

before(async () => { upstream = await startLoopbackUpstream(); });
after(async () => { await upstream.close(); });
beforeEach(() => upstream.reset());

describe('whisper bar client', () => {
  it('reads the whispers of the session with the DM bearer', async () => {
    upstream.reply(200, { whispers: [], total: 0, page: 1, limit: 20, narration_engine: 'none' });

    const listed = await fetchWhispers(SCOPE, opts());

    assert.equal(listed.narration_engine, 'none');
    assert.deepEqual(listed.whispers, []);
    const [req] = upstream.requests;
    assert.equal(req.method, 'GET');
    assert.equal(req.path, '/api/v1/watcher/whispers?session_id=sess-1&campaign_id=camp-1');
    assert.equal(req.headers.authorization, 'Bearer dm-token');
  });

  it('asks the narration port and rejects a refusal with its status', async () => {
    upstream.reply(502, { detail: 'Upstream service is unavailable', upstream: 'the_watcher' });

    await assert.rejects(generateWhispers(SCOPE, opts()), (err: unknown) => err instanceof HttpError && err.status === 502);
    const [req] = upstream.requests;
    assert.equal(req.method, 'POST');
    assert.equal(req.path, '/api/v1/watcher/whispers/generate');
    assert.deepEqual(JSON.parse(req.body), { session_id: 'sess-1', campaign_id: 'camp-1' });
  });

  it('reads the actions of the session', async () => {
    upstream.reply(200, [{ action_id: 'act-1', actor_name: 'Goblin', action_type: 'move', description: 'Runs', status: 'vetoed' }]);

    const actions = await fetchPendingActions(SCOPE, opts());

    assert.equal(actions[0].action_id, 'act-1');
    assert.equal(upstream.requests[0].path, '/api/v1/watcher/actions/pending?session_id=sess-1&campaign_id=camp-1');
  });
});

describe('openAction', () => {
  const action = (id: string, status: string) => ({ action_id: id, actor_name: 'G', action_type: 'move', description: 'd', status });

  it('picks the first action that waits for the DM', () => {
    assert.equal(openAction([action('a', 'vetoed'), action('b', 'pending'), action('c', 'modified')])?.action_id, 'b');
  });

  it('gives null when no action waits', () => {
    assert.equal(openAction([action('a', 'approved'), action('b', 'expired')]), null);
  });
});
