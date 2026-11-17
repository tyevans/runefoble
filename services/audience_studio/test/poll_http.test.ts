/**
 * Frontdoor tests for poll state durability and Redis publish recovery.
 * Governed by TASK-0575 and Hard Invariant 7 (public HTTP routes only).
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { MemoryEventStore } from '../src/eventStore/memoryEventStore.js';
import { InMemoryStreamPublisher } from '../src/memoryStreams.js';
import { buildServer } from '../src/server.js';
import { jsonBody } from './helpers.js';

const POLLS = '/api/v1/audience/polls';

async function start(
  store: MemoryEventStore,
  publisher: InMemoryStreamPublisher
) {
  const ctx = await buildServer({
    spicedbToken: '',
    logger: false,
    createAdapters: async () => ({ eventStore: store, streamPublisher: publisher }),
  });
  return ctx;
}

test('poll and its votes survive a restart', async () => {
  const store = new MemoryEventStore();
  const publisher = new InMemoryStreamPublisher();

  const first = await start(store, publisher);
  const created = jsonBody(
    await first.server.inject({
      method: 'POST',
      url: POLLS,
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
    payload: { voter_id: 'viewer-1', option_id: 'opt_1' },
  });
  assert.equal(vote.statusCode, 200);
  await first.server.close();

  const second = await start(store, publisher);
  const read = await second.server.inject({ method: 'GET', url: `${POLLS}/${created.id}` });
  assert.equal(read.statusCode, 200);
  const poll = jsonBody(read);
  assert.equal(poll.status, 'active');
  assert.equal(poll.totalVotes, 1);
  assert.equal(poll.options[0].votes, 1);

  const duplicate = await second.server.inject({
    method: 'POST',
    url: `${POLLS}/${created.id}/votes`,
    payload: { voter_id: 'viewer-1', option_id: 'opt_2' },
  });
  assert.equal(duplicate.statusCode, 400);
  assert.match(jsonBody(duplicate).error, /already voted/);
  await second.server.close();
});

test('a publish failure rejects the command and stores nothing', async () => {
  const store = new MemoryEventStore();
  const publisher = new InMemoryStreamPublisher();
  const ctx = await start(store, publisher);
  publisher.failNextPublishes(1);

  const res = await ctx.server.inject({
    method: 'POST',
    url: POLLS,
    payload: { campaign_id: 'camp-fail', title: 'T', prompt: 'P', options: ['A'] },
  });
  assert.equal(res.statusCode, 503);

  const list = jsonBody(await ctx.server.inject({ method: 'GET', url: POLLS }));
  assert.equal(list.polls.length, 0);
  await ctx.server.close();
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

  const first = await start(store, publisher);
  const created = jsonBody(
    await first.server.inject({
      method: 'POST',
      url: POLLS,
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
    payload: { voter_id: 'v', option_id: 'opt_2' },
  });
  await first.server.close();

  await new Promise((resolve) => setTimeout(resolve, 1100));

  const second = await start(store, publisher);
  await waitFor(() => publisher.published.some((e) => e.type.endsWith('poll_completed')));
  const completed = publisher.published.filter((e) => e.type.endsWith('poll_completed'));
  assert.equal(completed.length, 1);
  assert.equal(completed[0].data.winning_option_id, 'opt_2');

  const read = jsonBody(await second.server.inject({ method: 'GET', url: `${POLLS}/${created.id}` }));
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
