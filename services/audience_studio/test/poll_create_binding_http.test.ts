/**
 * Frontdoor tests for poll creation and the SpiceDB campaign binding (TASK-0849).
 * Only public HTTP routes are used for setup and reads. The event store and SpiceDB are
 * boundary doubles. Governed by ADR-0011 (the binding follows the commit) and ADR-0015 (a failed
 * dependency must not look like a working one).
 */

import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import type { AppendChange } from '../src/eventStore/types.js';
import { MemoryEventStore } from '../src/eventStore/memoryEventStore.js';
import { InMemoryStreamPublisher } from '../src/memoryStreams.js';
import { buildServer } from '../src/server.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';
import { bearer, jsonBody, TEST_AUDIENCE, TEST_ISSUER, TestIssuer } from './helpers.js';

const POLLS = '/api/v1/audience/polls';
const POLL_STREAM_PREFIX = 'AudiencePoll-';

let issuer: TestIssuer;
const spicedb = new FakeSpiceDb();

before(async () => {
  issuer = await TestIssuer.start();
});

after(async () => {
  await issuer.close();
});

/** Event store boundary double. It records every append attempt and can fail the next one. */
class AppendFaultStore extends MemoryEventStore {
  readonly attempts: string[] = [];
  private failNext = false;

  failNextAppend(): void {
    this.failNext = true;
  }

  override async appendAll(changes: AppendChange[]): Promise<void> {
    this.attempts.push(...changes.map((change) => change.streamId));
    if (this.failNext) {
      this.failNext = false;
      throw new Error('append failed (test double)');
    }
    await super.appendAll(changes);
  }
}

async function start(store: MemoryEventStore) {
  return buildServer({
    spicedb,
    logger: false,
    zitadel: { issuer: TEST_ISSUER, audience: TEST_AUDIENCE, internalUrl: issuer.internalUrl },
    createAdapters: async () => ({ eventStore: store, streamPublisher: new InMemoryStreamPublisher() }),
  });
}

function pollPayload(campaignId: string) {
  return { campaign_id: campaignId, title: 'Binding', prompt: 'Bound?', options: ['Yes', 'No'], quorum: 1 };
}

test('a failed append rejects the create with a 5xx and leaves no poll and no campaign binding', async () => {
  const store = new AppendFaultStore();
  const ctx = await start(store);
  spicedb.grant('camp-append', 'dungeon_master', 'dm-append');
  store.failNextAppend();

  const res = await ctx.server.inject({
    method: 'POST',
    url: POLLS,
    headers: bearer(await issuer.mint('dm-append')),
    payload: pollPayload('camp-append'),
  });
  assert.ok(res.statusCode >= 500 && res.statusCode < 600, `expected 5xx, got ${res.statusCode}`);

  const attempted = store.attempts.filter((id) => id.startsWith(POLL_STREAM_PREFIX));
  assert.equal(attempted.length, 1);
  const pollId = attempted[0].slice(POLL_STREAM_PREFIX.length);

  const read = await ctx.server.inject({
    method: 'GET',
    url: `${POLLS}/${pollId}`,
    headers: bearer(await issuer.mint('dm-append')),
  });
  assert.equal(read.statusCode, 404);

  const bound = await spicedb.checkPermission({
    resource: { objectType: 'audience_poll', objectId: pollId },
    permission: 'view',
    subject: { objectType: 'user', objectId: 'dm-append' },
  });
  assert.equal(bound, false, 'no campaign binding may exist for a poll that was not stored');
  await ctx.server.close();
});

test('a failed campaign binding after the commit returns 503 and never reports the poll as created', async () => {
  const store = new AppendFaultStore();
  const ctx = await start(store);
  spicedb.grant('camp-bind', 'dungeon_master', 'dm-bind');
  spicedb.setWritesUnavailable(true);
  try {
    const res = await ctx.server.inject({
      method: 'POST',
      url: POLLS,
      headers: bearer(await issuer.mint('dm-bind')),
      payload: pollPayload('camp-bind'),
    });
    assert.equal(res.statusCode, 503);
    assert.doesNotMatch(res.body, /"id"/);
  } finally {
    spicedb.setWritesUnavailable(false);
  }
  await ctx.server.close();
});

test('a created poll is visible to a campaign member through the public GET', async () => {
  const store = new AppendFaultStore();
  const ctx = await start(store);
  spicedb.grant('camp-visible', 'dungeon_master', 'dm-visible');
  spicedb.grant('camp-visible', 'spectator', 'viewer-visible');

  const created = await ctx.server.inject({
    method: 'POST',
    url: POLLS,
    headers: bearer(await issuer.mint('dm-visible')),
    payload: pollPayload('camp-visible'),
  });
  assert.equal(created.statusCode, 201);
  const id = jsonBody(created).id;

  const read = await ctx.server.inject({
    method: 'GET',
    url: `${POLLS}/${id}`,
    headers: bearer(await issuer.mint('viewer-visible')),
  });
  assert.equal(read.statusCode, 200);
  assert.equal(jsonBody(read).id, id);
  await ctx.server.close();
});
