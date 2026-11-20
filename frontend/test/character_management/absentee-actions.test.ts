/**
 * The absentee stance drawer shows the real stand-in state and the saved stance (TASK-0954).
 *
 * The gateway is faked at the fetch boundary. Opening the drawer reads the character and its
 * guardrail policy. Saving a stance writes the full policy. The drawer shows a stance only after
 * the gateway confirms it. Governing ADRs: ADR-0015, ADR-0013.
 */

import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';
import { openAbsenteeDrawer, saveAbsenteeStance } from '../../src/app/absentee-actions.ts';

interface Host {
  activeCharacter: any;
  characters: any[];
  absenteeStance: string;
  isAbsenteeDirectiveOpen: boolean;
  toasts: string[];
  showToast(m: string): void;
}

function makeHost(): Host {
  const char = { id: 'char-7', name: 'Seoni', isAiStandIn: false };
  return {
    activeCharacter: char,
    characters: [char],
    absenteeStance: '',
    isAbsenteeDirectiveOpen: false,
    toasts: [],
    showToast(m: string) { this.toasts.push(m); },
  };
}

describe('opening the stance drawer reads the real stand-in state', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('takes the stand-in flag from the character and the stance from the stored policy', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-7': { body: { id: 'char-7', name: 'Seoni', isAiStandIn: true, owner_id: 'user-seoni' } },
      'GET /api/v1/characters/char-7/guardrails': { body: { stance: 'cautious' } },
    });
    const host = makeHost();

    await openAbsenteeDrawer(host as any);

    assert.equal(host.isAbsenteeDirectiveOpen, true);
    assert.equal(host.activeCharacter.isAiStandIn, true);
    assert.equal(host.characters[0].isAiStandIn, true);
    assert.equal(host.absenteeStance, 'cautious');
  });

  it('shows no stance when the player has not chosen one', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-7': { body: { id: 'char-7', isAiStandIn: true, owner_id: 'user-seoni' } },
      'GET /api/v1/characters/char-7/guardrails': { body: { stance: null } },
    });
    const host = makeHost();

    await openAbsenteeDrawer(host as any);

    assert.equal(host.absenteeStance, '');
  });

  it('keeps the drawer closed and shows the server message when the read fails', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-7': { status: 503, body: { detail: 'Character service is unavailable.' } },
      'GET /api/v1/characters/char-7/guardrails': { body: { stance: 'heroic' } },
    });
    const host = makeHost();

    await openAbsenteeDrawer(host as any);

    assert.equal(host.isAbsenteeDirectiveOpen, false);
    assert.equal(host.absenteeStance, '');
    assert.equal(host.toasts.length, 1);
    assert.match(host.toasts[0], /^Stance drawer not opened\. /);
  });
});

describe('saving a stance writes the policy and shows it only after the gateway confirms', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('sends the chosen stance with the stored policy and then shows it', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-7/guardrails': { body: { stance: 'defensive', avoid_melee: true } },
      'PUT /api/v1/characters/char-7/guardrails': { body: {} },
    });
    const host = makeHost();

    await saveAbsenteeStance(host as any, 'heroic');

    assert.deepEqual(gateway.calls[1].body, { stance: 'heroic', avoid_melee: true });
    assert.equal(host.absenteeStance, 'heroic');
    assert.deepEqual(host.toasts, ['Tactical stance saved: heroic']);
  });

  it('keeps the old stance and shows the server message when the write is refused', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-7/guardrails': { body: { stance: 'defensive' } },
      'PUT /api/v1/characters/char-7/guardrails': { status: 422, body: { detail: 'stance must be defensive, cautious or heroic' } },
    });
    const host = makeHost();
    host.absenteeStance = 'defensive';

    await saveAbsenteeStance(host as any, 'heroic');

    assert.equal(host.absenteeStance, 'defensive');
    assert.deepEqual(host.toasts, ['Stance not saved. stance must be defensive, cautious or heroic']);
  });
});
