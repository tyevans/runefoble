/**
 * Frontdoor tests for poll state durability and Redis publish recovery.
 * Governed by TASK-0575 and Hard Invariant 7 (public HTTP routes only).
 */

import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { MemoryEventStore } from '../src/eventStore/memoryEventStore.js';
import { InMemoryStreamPublisher } from '../src/memoryStreams.js';
import { buildServer } from '../src/server.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';
import { bearer, jsonBody, TEST_AUDIENCE, TEST_ISSUER, TestIssuer } from './helpers.js';

const POLLS = '/api/v1/audience/polls';

let issuer: TestIssuer;
/** One authorization store for every process in this file. A restart does not reset SpiceDB. */
const spicedb = new FakeSpiceDb();

before(async () => {
  issuer = await TestIssuer.start();
});

after(async () => {
  await issuer.close();
});

/**
 * Database boundary double. The next `count` poll reads wait in pairs, so two writers
 * read the same stream version before either one appends.
 */
class PollReadBarrier extends MemoryEventStore {
  private remaining = 0;
  private waiting: Array<() => void> = [];

  holdNextPollReads(count: number): void {
    this.remaining = count;
  }

  override async load(streamId: string) {
    const events = await super.load(streamId);
    if (this.remaining === 0 || !streamId.startsWith('AudiencePoll-')) return events;
    this.remaining -= 1;
    await new Promise<void>((resolve) => {
      this.waiting.push(resolve);
      if (this.waiting.length === 2) {
        const release = this.waiting;
        this.waiting = [];
        release.forEach((r) => r());
      }
    });
    return events;
  }
}

async function start(
  store: MemoryEventStore,
  publisher: InMemoryStreamPublisher,
  options: { outboxIntervalMs?: number } = {}
) {
  const ctx = await buildServer({
    spicedb,
    logger: false,
    zitadel: { issuer: TEST_ISSUER, audience: TEST_AUDIENCE, internalUrl: issuer.internalUrl },
    createAdapters: async () => ({ eventStore: store, streamPublisher: publisher }),
    outboxIntervalMs: options.outboxIntervalMs,
  });
  return ctx;
}

test('poll and its votes survive a restart', async () => {
  const store = new MemoryEventStore();
  const publisher = new InMemoryStreamPublisher();
  spicedb.grant('camp-restart', 'dungeon_master', 'dm-restart');
  spicedb.grant('camp-restart', 'spectator', 'viewer-1');

  const first = await start(store, publisher);
  const created = jsonBody(
    await first.server.inject({
      method: 'POST',
      url: POLLS,
      headers: bearer(await issuer.mint('dm-restart')),
      payload: {
        campaign_id: 'camp-restart',
        title: 'Restart Poll',
        prompt: 'Survive?',
        options: ['Yes', 'No'],
        duration_seconds: 600,
        quorum: 2,
      },
    })
  );
  const vote = await first.server.inject({
    method: 'POST',
    url: `${POLLS}/${created.id}/votes`,
    headers: bearer(await issuer.mint('viewer-1')),
    payload: { option_id: 'opt_1' },
  });
  assert.equal(vote.statusCode, 200);
  await first.server.close();

  const second = await start(store, publisher);
  const read = await second.server.inject({
    method: 'GET',
    url: `${POLLS}/${created.id}`,
    headers: bearer(await issuer.mint('viewer-1')),
  });
  assert.equal(read.statusCode, 200);
  const poll = jsonBody(read);
  assert.equal(poll.status, 'active');
  assert.equal(poll.totalVotes, 1);
  assert.equal(poll.options[0].votes, 1);

  const duplicate = await second.server.inject({
    method: 'POST',
    url: `${POLLS}/${created.id}/votes`,
    headers: bearer(await issuer.mint('viewer-1')),
    payload: { option_id: 'opt_2' },
  });
  assert.equal(duplicate.statusCode, 400);
  assert.match(jsonBody(duplicate).error, /already voted/);
  await second.server.close();
});

test('a publish failure after the append keeps the event pending until the relay publishes it', async () => {
  const store = new MemoryEventStore();
  const publisher = new InMemoryStreamPublisher();
  const ctx = await start(store, publisher, { outboxIntervalMs: 20 });
  spicedb.grant('camp-fail', 'dungeon_master', 'dm-fail');
  publisher.failNextPublishes(1);

  const res = await ctx.server.inject({
    method: 'POST',
    url: POLLS,
    headers: bearer(await issuer.mint('dm-fail')),
    payload: { campaign_id: 'camp-fail', title: 'T', prompt: 'P', options: ['A'] },
  });
  assert.equal(res.statusCode, 201);
  const created = jsonBody(res);
  assert.equal(publisher.published.length, 0);

  await waitFor(() => publisher.published.some((e) => e.type.endsWith('poll_started')));
  assert.deepEqual(
    publisher.published.map((e) => e.id),
    [`AudiencePoll-${created.id}#1`]
  );

  const list = jsonBody(
    await ctx.server.inject({ method: 'GET', url: POLLS, headers: bearer(await issuer.mint('dm-fail')) })
  );
  assert.equal(list.polls.length, 1);
  await ctx.server.close();
});

test('two votes from two replicas on one poll: one is recorded and the other gets 409', async () => {
  const store = new PollReadBarrier();
  const publisher = new InMemoryStreamPublisher();
  const replicaA = await start(store, publisher);
  const replicaB = await start(store, publisher);
  spicedb.grant('camp-race', 'dungeon_master', 'dm-race');
  spicedb.grant('camp-race', 'spectator', 'racer-1');
  spicedb.grant('camp-race', 'spectator', 'racer-2');
  const created = jsonBody(
    await replicaA.server.inject({
      method: 'POST',
      url: POLLS,
      headers: bearer(await issuer.mint('dm-race')),
      payload: { campaign_id: 'camp-race', title: 'Race', prompt: 'Who wins?', options: ['Left', 'Right'] },
    })
  );

  store.holdNextPollReads(4);
  const [a, b] = await Promise.all([
    replicaA.server.inject({
      method: 'POST',
      url: `${POLLS}/${created.id}/votes`,
      headers: bearer(await issuer.mint('racer-1')),
      payload: { option_id: 'opt_1' },
    }),
    replicaB.server.inject({
      method: 'POST',
      url: `${POLLS}/${created.id}/votes`,
      headers: bearer(await issuer.mint('racer-2')),
      payload: { option_id: 'opt_2' },
    }),
  ]);

  assert.deepEqual([a.statusCode, b.statusCode].sort(), [200, 409]);
  const loser = a.statusCode === 409 ? a : b;
  assert.match(jsonBody(loser).error, /retry/i);

  const read = jsonBody(
    await replicaA.server.inject({
      method: 'GET',
      url: `${POLLS}/${created.id}`,
      headers: bearer(await issuer.mint('dm-race')),
    })
  );
  assert.equal(read.totalVotes, 1);
  await replicaA.server.close();
  await replicaB.server.close();
});

test('readyz reports 503 while the stream is unavailable and 200 after recovery', async () => {
  const store = new MemoryEventStore();
  const publisher = new InMemoryStreamPublisher();
  const ctx = await start(store, publisher);

  publisher.setReachable(false);
  const down = await ctx.server.inject({ method: 'GET', url: '/readyz' });
  assert.equal(down.statusCode, 503);

  publisher.setReachable(true);
  const up = await ctx.server.inject({ method: 'GET', url: '/readyz' });
  assert.equal(up.statusCode, 200);
  await ctx.server.close();
});

test('a poll with a short window closes after a restart and publishes completion', async () => {
  const store = new MemoryEventStore();
  const publisher = new InMemoryStreamPublisher();

  spicedb.grant('camp-window', 'dungeon_master', 'dm-window');
  spicedb.grant('camp-window', 'spectator', 'v');
  const first = await start(store, publisher);
  const created = jsonBody(
    await first.server.inject({
      method: 'POST',
      url: POLLS,
      headers: bearer(await issuer.mint('dm-window')),
      payload: {
        campaign_id: 'camp-window',
        title: 'Short',
        prompt: 'Window',
        options: ['A', 'B'],
        duration_seconds: 1,
        quorum: 1,
      },
    })
  );
  await first.server.inject({
    method: 'POST',
    url: `${POLLS}/${created.id}/votes`,
    headers: bearer(await issuer.mint('v')),
    payload: { option_id: 'opt_2' },
  });
  await first.server.close();

  await new Promise((resolve) => setTimeout(resolve, 1100));

  const second = await start(store, publisher);
  await waitFor(() => publisher.published.some((e) => e.type.endsWith('poll_completed')));
  const completed = publisher.published.filter((e) => e.type.endsWith('poll_completed'));
  assert.equal(completed.length, 1);
  assert.equal(completed[0].data.winning_option_id, 'opt_2');

  const read = jsonBody(
    await second.server.inject({
      method: 'GET',
      url: `${POLLS}/${created.id}`,
      headers: bearer(await issuer.mint('dm-window')),
    })
  );
  assert.equal(read.status, 'completed');
  await second.server.close();
});

async function waitFor(check: () => boolean, timeoutMs = 3000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (!check()) {
    if (Date.now() > deadline) throw new Error('condition not met before timeout');
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
}
