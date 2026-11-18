/**
 * Developer entrypoint test. The `dev` script starts the service from TypeScript source and
 * must serve the public health route (ADR-0015 decision c keeps the health probes public).
 */

import assert from 'node:assert/strict';
import { spawn, type ChildProcess } from 'node:child_process';
import { createServer as createHttpServer, type Server } from 'node:http';
import { createServer } from 'node:net';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const PACKAGE_ROOT = fileURLToPath(new URL('../../', import.meta.url));
const children: ChildProcess[] = [];

after(() => {
  for (const child of children) {
    if (child.pid !== undefined && child.exitCode === null && child.signalCode === null) {
      process.kill(-child.pid, 'SIGTERM');
    }
  }
});

async function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      probe.close(() => (typeof address === 'object' && address ? resolve(address.port) : reject(new Error('no port'))));
    });
  });
}

/** Stands in for Zitadel's discovery document and JWKS endpoint. Start-up reads both. */
async function startJwksStub(): Promise<Server> {
  const server = createHttpServer((req, res) => {
    if (req.url === '/.well-known/openid-configuration') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ jwks_uri: 'http://zitadel.test/oauth/v2/keys' }));
      return;
    }
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ keys: [] }));
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  return server;
}

async function waitForHealth(url: string, timeoutMs: number): Promise<Response> {
  const deadline = Date.now() + timeoutMs;
  let lastError: unknown;
  while (Date.now() < deadline) {
    try {
      return await fetch(url);
    } catch (err) {
      lastError = err;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  throw new Error(`dev server did not answer ${url}: ${String(lastError)}`);
}

test('the dev script starts the service and serves GET /healthz', async () => {
  const port = await freePort();
  const jwks = await startJwksStub();
  after(() => jwks.close());
  const jwksPort = (jwks.address() as { port: number }).port;
  // NODE_ENV=test selects the in-memory adapters, so the dev server needs no Postgres or Redis.
  const child = spawn('pnpm', ['run', 'dev'], {
    cwd: PACKAGE_ROOT,
    detached: true,
    stdio: 'ignore',
    env: {
      ...process.env,
      NODE_ENV: 'test',
      PORT: String(port),
      HOST: '127.0.0.1',
      RUNEFOBLE_ZITADEL_ISSUER: 'http://zitadel.test',
      RUNEFOBLE_ZITADEL_AUDIENCE: 'runefoble-api',
      RUNEFOBLE_ZITADEL_INTERNAL_URL: `http://127.0.0.1:${jwksPort}`,
      RUNEFOBLE_SPICEDB_ENDPOINT: '127.0.0.1:50051',
      RUNEFOBLE_SPICEDB_PRESHARED_KEY: 'test-only',
    },
  });
  children.push(child);

  const response = await waitForHealth(`http://127.0.0.1:${port}/healthz`, 60_000);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: 'ok', service: 'audience_studio' });
});
