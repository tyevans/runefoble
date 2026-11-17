/**
 * Domain tests for PollAggregate and ProposalAggregate.
 * Commands run on the aggregate. Events are replayed to rebuild state.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { PollAggregate } from '../src/domain/pollAggregate.js';
import { ProposalAggregate } from '../src/domain/proposalAggregate.js';
import { DomainError } from '../src/errors.js';
import type { StoredEvent } from '../src/eventStore/types.js';

const start = new Date('2026-11-17T10:00:00.000Z');

/** Starts a poll, then reloads it from its stored events, as a restart would. */
function startPoll(quorum: number, durationSeconds = 60): PollAggregate {
  const created = new PollAggregate('poll-1');
  created.start({
    campaignId: 'camp-1',
    title: 'Hazard',
    prompt: 'Pick one',
    options: ['Fire', 'Acid'],
    durationSeconds,
    quorum,
    now: start,
  });
  const loaded = new PollAggregate('poll-1');
  loaded.rehydrate(persist(created));
  return loaded;
}

/** Turns uncommitted events into stored events, as the repository does. */
function persist(agg: { uncommitted: { streamId: string; expectedVersion: number; events: Array<{ type: string; data: Record<string, unknown>; occurredAt: string }> } | undefined }): StoredEvent[] {
  const change = agg.uncommitted!;
  return change.events.map((e, i) => ({
    streamId: change.streamId,
    version: change.expectedVersion + i + 1,
    type: e.type,
    data: e.data,
    occurredAt: e.occurredAt,
  }));
}

test('a started poll emits poll_started and rebuilds from events', () => {
  const created = new PollAggregate('poll-1');
  created.start({
    campaignId: 'camp-1', title: 'Hazard', prompt: 'Pick one',
    options: ['Fire', 'Acid'], durationSeconds: 60, quorum: 1, now: start,
  });
  const stored = persist(created);
  assert.equal(stored.length, 1);
  assert.equal(stored[0].type, 'runefoble.events.audience.poll_started');

  const replayed = new PollAggregate('poll-1');
  replayed.rehydrate(stored);
  replayed.vote('voter-1', 'opt_1', 'web', new Date('2026-11-17T10:00:05.000Z'));
  assert.equal(replayed.snapshot().totalVotes, 1);
  assert.equal(replayed.snapshot().options[0].votes, 1);
});

test('a voter cannot vote twice and an unknown option is refused', () => {
  const poll = startPoll(1);
  poll.vote('voter-1', 'opt_1', 'web', start);
  assert.throws(() => poll.vote('voter-1', 'opt_2', 'web', start), DomainError);
  assert.throws(() => poll.vote('voter-2', 'opt_9', 'web', start), /not found/);
});

test('votes after the window are refused', () => {
  const poll = startPoll(1, 10);
  const late = new Date(start.getTime() + 10_000);
  assert.throws(() => poll.vote('voter-1', 'opt_1', 'web', late), /no longer active/);
});

test('closing with quorum met returns a pending proposal for the winning option', () => {
  const poll = startPoll(2);
  poll.vote('a', 'opt_2', 'web', start);
  poll.vote('b', 'opt_2', 'web', start);
  const closeAt = new Date(start.getTime() + 1000);
  const draft = poll.close('prop-1', closeAt);
  assert.ok(draft);
  assert.equal(draft.status, 'pending');
  assert.equal(draft.parameters.winningOptionId, 'opt_2');
  assert.equal(poll.snapshot().status, 'completed');
});

test('closing below quorum returns no proposal', () => {
  const poll = startPoll(5);
  poll.vote('a', 'opt_1', 'web', start);
  assert.equal(poll.close('prop-1', start), undefined);
  assert.equal(poll.snapshot().quorumMet, false);
});

test('a proposal can be approved once and not decided again', () => {
  const created = new ProposalAggregate('prop-1');
  created.propose({
    id: 'prop-1',
    pollId: 'poll-1',
    campaignId: 'camp-1',
    title: 'Hazard: Fire',
    modifierType: 'chaos_modifier',
    description: 'd',
    parameters: { winningOptionId: 'opt_1' },
    status: 'pending',
    createdAt: start.toISOString(),
  });
  const proposal = new ProposalAggregate('prop-1');
  proposal.rehydrate(persist(created));
  proposal.approve('dm-1', start);
  assert.equal(proposal.snapshot()?.status, 'approved');
  assert.throws(() => proposal.reject('dm-1', start), /already approved/);
});
