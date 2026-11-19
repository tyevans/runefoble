/**
 * Unit tests for the order of PollEngine.createPoll (TASK-0849, ADR-0011).
 * The engine runs over the real repository and access layer. Only the store and SpiceDB are doubles.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { AudienceAccess } from '../src/access/audienceAccess.js';
import { ApprovalQueue } from '../src/approvalQueue.js';
import { DependencyUnavailableError } from '../src/errors.js';
import { MemoryEventStore } from './fakes/memoryEventStore.js';
import { AudienceEventRepository } from '../src/eventSourcing/repository.js';
import { KeyedMutex } from '../src/eventSourcing/keyedMutex.js';
import { OutboxRelay } from '../src/eventSourcing/outboxRelay.js';
import { PollEngine } from '../src/pollEngine.js';
import { InMemoryStreamPublisher } from './fakes/memoryStreams.js';
import type { Logger } from '../src/logger.js';
import type { RelationshipWrite } from '../src/spicedb/spicedbPort.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';

interface Harness {
  store: MemoryEventStore;
  spicedb: FakeSpiceDb;
  engine: PollEngine;
  errors: Array<Record<string, unknown>>;
}

function harness(): Harness {
  const store = new MemoryEventStore();
  const spicedb = new FakeSpiceDb();
  const errors: Array<Record<string, unknown>> = [];
  const log = {
    info: () => {},
    warn: () => {},
    error: (obj: Record<string, unknown>) => {
      errors.push(obj);
    },
  } as unknown as Logger;
  const access = new AudienceAccess(spicedb);
  const relay = new OutboxRelay(store, new InMemoryStreamPublisher(), log, 60_000);
  const repo = new AudienceEventRepository(store, relay);
  const mutex = new KeyedMutex();
  const approvalQueue = new ApprovalQueue(access, repo, mutex, log);
  const engine = new PollEngine(repo, mutex, approvalQueue, access, log);
  return { store, spicedb, engine, errors };
}

const dm = { userId: 'dm-order', username: 'dm-order' };
const params = { campaignId: 'camp-order', title: 'Order', prompt: 'Order?', options: ['A', 'B'] };

test('the poll events are stored before the campaign binding is written', async () => {
  const { store, spicedb, engine } = harness();
  spicedb.grant('camp-order', 'dungeon_master', 'dm-order');
  const storedAtBind: number[] = [];
  const write = spicedb.writeRelationship.bind(spicedb);
  spicedb.writeRelationship = async (w: RelationshipWrite) => {
    storedAtBind.push((await store.load(`AudiencePoll-${w.resource.objectId}`)).length);
    return write(w);
  };

  const poll = await engine.createPoll(dm, params);

  assert.deepEqual(storedAtBind, [1], 'the binding must see one stored poll event');
  assert.equal((await store.load(`AudiencePoll-${poll.id}`)).length, 1);
  engine.close();
});

test('a failed binding after the commit raises a dependency outage and logs the poll id', async () => {
  const { store, spicedb, engine, errors } = harness();
  spicedb.grant('camp-order', 'dungeon_master', 'dm-order');
  spicedb.setWritesUnavailable(true);

  await assert.rejects(engine.createPoll(dm, params), DependencyUnavailableError);

  const [logged] = errors;
  assert.ok(logged, 'the failed binding must be logged');
  assert.equal(typeof logged.pollId, 'string');
  const stored = await store.loadPrefix('AudiencePoll-');
  assert.equal(stored.length, 1, 'the committed poll stays stored');
  engine.close();
});
