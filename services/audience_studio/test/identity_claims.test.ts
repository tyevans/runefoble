/**
 * Frontdoor tests for the principal that ZitadelVerifier returns (TASK-0890, ADR-0015).
 * The verifier reads discovery and signing keys from a Zitadel-like issuer over HTTP.
 * The username comes only from `preferred_username`. The verifier never makes one from `sub`.
 */

import assert from 'node:assert/strict';
import { after, before, describe, test } from 'node:test';
import { ZitadelVerifier } from '../src/identity/zitadelVerifier.js';
import { TEST_AUDIENCE, TEST_ISSUER, TestIssuer } from './helpers.js';

let issuer: TestIssuer;
let verifier: ZitadelVerifier;

before(async () => {
  issuer = await TestIssuer.start();
  verifier = await ZitadelVerifier.create({
    issuer: TEST_ISSUER,
    audience: TEST_AUDIENCE,
    internalUrl: issuer.internalUrl,
  });
});

after(async () => {
  await issuer.close();
});

describe('the verified username comes from preferred_username only', () => {
  test('a token with preferred_username yields that username', async () => {
    const principal = await verifier.verify(await issuer.mint('user-evelyn', { preferredUsername: 'evelyn' }));
    assert.equal(principal.userId, 'user-evelyn');
    assert.equal(principal.username, 'evelyn');
  });

  test('a token without preferred_username yields a null username', async () => {
    const principal = await verifier.verify(await issuer.mint('user-marcus', { preferredUsername: null }));
    assert.equal(principal.userId, 'user-marcus');
    assert.equal(principal.username, null);
  });

  test('an empty preferred_username yields a null username', async () => {
    const principal = await verifier.verify(await issuer.mint('user-sarah', { preferredUsername: '' }));
    assert.equal(principal.username, null);
  });
});
