/**
 * Unit tests for the event store contract and the keyed mutex.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { MemoryEventStore } from '../src/eventStore/memoryEventStore.js';
import { ConcurrencyConflictError } from '../src/eventStore/types.js';
import { KeyedMutex } from '../src/eventSourcing/keyedMutex.js';

const at = '2026-11-17T00:00:00.000Z';

test('appendAll writes every stream or none when one stream conflicts', async () => {
  const store = new MemoryEventStore();
  await store.appendAll([
    { streamId: 'AudiencePoll-a', expectedVersion: 0, events: [{ type: 't.started', data: {}, occurredAt: at }] },
  ]);

  await assert.rejects(
    store.appendAll([
      { streamId: 'AudienceModifierProposal-new', expectedVersion: 0, events: [{ type: 't.proposed', data: {}, occurredAt: at }] },
      { streamId: 'AudiencePoll-a', expectedVersion: 0, events: [{ type: 't.completed', data: {}, occurredAt: at }] },
    ]),
    ConcurrencyConflictError
  );

  assert.deepEqual(await store.load('AudienceModifierProposal-new'), []);
  const poll = await store.load('AudiencePoll-a');
  assert.equal(poll.length, 1);
  assert.equal(poll[0].version, 1);
});

test('load returns events in version order and loadPrefix filters by stream prefix', async () => {
  const store = new MemoryEventStore();
  await store.appendAll([
    { streamId: 'AudiencePoll-1', expectedVersion: 0, events: [{ type: 'a', data: {}, occurredAt: at }] },
    { streamId: 'AudienceModifierProposal-1', expectedVersion: 0, events: [{ type: 'b', data: {}, occurredAt: at }] },
  ]);
  await store.appendAll([
    { streamId: 'AudiencePoll-1', expectedVersion: 1, events: [{ type: 'c', data: {}, occurredAt: at }] },
  ]);

  const polls = await store.loadPrefix('AudiencePoll-');
  assert.deepEqual(polls.map((e) => [e.streamId, e.version, e.type]), [
    ['AudiencePoll-1', 1, 'a'],
    ['AudiencePoll-1', 2, 'c'],
  ]);
});

test('KeyedMutex runs work on the same key one at a time', async () => {
  const mutex = new KeyedMutex();
  const trace: string[] = [];
  const slow = (label: string, ms: number) =>
    mutex.run(['poll-1'], async () => {
      trace.push(`${label}:start`);
      await new Promise((r) => setTimeout(r, ms));
      trace.push(`${label}:end`);
    });
  await Promise.all([slow('a', 30), slow('b', 1)]);
  assert.deepEqual(trace, ['a:start', 'a:end', 'b:start', 'b:end']);
});
