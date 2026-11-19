/**
 * Unit tests for JWT payload decoding and claim extraction (TASK-0871).
 * Fixed token strings only. No live Zitadel tokens.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { extractClaimsFromPayload, parseJwtPayload } from '../src/auth/claims.ts';

function jwtWith(payload: Record<string, unknown>): string {
  return `header.${Buffer.from(JSON.stringify(payload)).toString('base64url')}.signature`;
}

describe('parseJwtPayload (TASK-0871)', () => {
  it('decodes a base64url payload that holds non-ASCII text', () => {
    const token = jwtWith({ sub: 'user-7', name: 'Zoë >>> ???' });
    assert.deepEqual(parseJwtPayload(token), { sub: 'user-7', name: 'Zoë >>> ???' });
  });

  it('returns null when the payload is not JSON', () => {
    const token = `header.${Buffer.from('not json').toString('base64url')}.signature`;
    assert.equal(parseJwtPayload(token), null);
  });

  it('returns null when the token has no payload segment', () => {
    assert.equal(parseJwtPayload('only-one-segment'), null);
  });
});

describe('extractClaimsFromPayload (TASK-0871)', () => {
  it('reads roles from the Zitadel project claim when it is a list', () => {
    const claims = extractClaimsFromPayload({
      sub: 'user-1',
      'urn:zitadel:iam:org:project:roles': ['player'],
    });
    assert.deepEqual(claims.roles, ['player']);
  });

  it('reads role names from the keys when roles arrive as an object', () => {
    const claims = extractClaimsFromPayload({
      sub: 'user-1',
      'urn:zitadel:iam:org:project:roles': { dm: { 'org-1': 'Org' }, player: {} },
    });
    assert.deepEqual(claims.roles, ['dm', 'player']);
  });

  it('uses an empty role list when no roles claim exists', () => {
    assert.deepEqual(extractClaimsFromPayload({ sub: 'user-1' }).roles, []);
  });

  it('falls back to user_id, then to a fixed placeholder, when sub is missing', () => {
    assert.equal(extractClaimsFromPayload({ user_id: 'legacy-9' }).user_id, 'legacy-9');
    assert.equal(extractClaimsFromPayload({}).user_id, 'user-unknown');
  });

  it('takes the username from preferred_username, then username, then name', () => {
    assert.equal(extractClaimsFromPayload({ sub: 's', preferred_username: 'pref', username: 'u', name: 'n' }).username, 'pref');
    assert.equal(extractClaimsFromPayload({ sub: 's', username: 'u', name: 'n' }).username, 'u');
    assert.equal(extractClaimsFromPayload({ sub: 's', name: 'n' }).username, 'n');
  });

  it('takes the avatar from avatar_url, then from picture', () => {
    assert.equal(extractClaimsFromPayload({ sub: 's', picture: 'p.png' }).avatar_url, 'p.png');
    assert.equal(extractClaimsFromPayload({ sub: 's', avatar_url: 'a.png', picture: 'p.png' }).avatar_url, 'a.png');
  });

  it('leaves optional fields undefined when the payload omits them', () => {
    const claims = extractClaimsFromPayload({ sub: 'user-1' });
    assert.equal(claims.email, undefined);
    assert.equal(claims.display_name, undefined);
    assert.equal(claims.bio, undefined);
  });
});
