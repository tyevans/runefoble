/**
 * Gherkin steps for the identity refusal scenarios (TASK-0535).
 * Governed by ADR-0014, Hard Invariant 7, US-0062, and US-0013.
 *
 * The forged token is signed with a key that the platform does not trust. It is built with
 * Node crypto from the public token format. No step writes identity state.
 */

import { expect } from '@playwright/test';
import { createSign, generateKeyPairSync } from 'node:crypto';
import { Given, When, Then } from '../support/fixtures';

const API_BASE = (process.env.PLAYWRIGHT_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const ISSUER = process.env.PLAYWRIGHT_ZITADEL_ISSUER || 'http://auth.localhost';
const AUDIENCE = process.env.PLAYWRIGHT_ZITADEL_AUDIENCE || 'runefoble-api';
const ABSENT_STATUSES = [404, 405];

function forgeRs256Token(subject: string): string {
  const { privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const header = Buffer.from(
    JSON.stringify({ alg: 'RS256', typ: 'JWT', kid: 'key-untrusted-forgery' })
  ).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(
    JSON.stringify({ sub: subject, iss: ISSUER, aud: AUDIENCE, iat: now, exp: now + 3600 })
  ).toString('base64url');
  const signer = createSign('RSA-SHA256');
  signer.update(`${header}.${payload}`);
  return `${header}.${payload}.${signer.sign(privateKey, 'base64url')}`;
}

Given('the public API is reachable', async ({ frontdoorApi }) => {
  const health = await frontdoorApi.checkHealth();
  expect(health.status).toBeTruthy();
});

Given('I hold a token signed by a key the platform does not trust', async ({ world }) => {
  world.set('forgedToken', forgeRs256Token('user-forged-probe'));
});

When('I request my profile from the public API with that token', async ({ request, world }) => {
  const token = world.get<string>('forgedToken');
  expect(token, 'a forged token must be set by the Given step').toBeTruthy();
  const res = await request.get(`${API_BASE}/api/v1/profile`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  world.set('lastStatus', res.status());
});

Then('the API refuses the request with status {int}', async ({ world }, status: number) => {
  expect(world.get<number>('lastStatus')).toBe(status);
});

When('I call the retired sign-in endpoint {string}', async ({ request, world }, path: string) => {
  const res = await request.post(`${API_BASE}${path}`, { data: {} });
  world.set('lastStatus', res.status());
});

When(
  'I send a sync request to {string} that names the role {string}',
  async ({ request, world }, path: string, role: string) => {
    const res = await request.post(`${API_BASE}${path}`, {
      data: { user_id: 'user-victim', roles: [role] },
    });
    world.set('lastStatus', res.status());
  }
);

Then('the API reports the route as absent', async ({ world }) => {
  expect(ABSENT_STATUSES).toContain(world.get<number>('lastStatus'));
});
