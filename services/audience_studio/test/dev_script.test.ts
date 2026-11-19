/**
 * Developer entrypoint test. The `dev` script starts the service from TypeScript source. The
 * source applies the start-up checks, so a missing event store stops the dev server before it
 * listens (ADR-0015 decision f). The built-process tests in `tests/` cover `GET /healthz`.
 */

import assert from 'node:assert/strict';
import { spawn, type ChildProcess } from 'node:child_process';
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

/** Collects the child's stderr until it contains `pattern`, or fails after `timeoutMs`. */
async function waitForStderr(child: ChildProcess, pattern: RegExp, timeoutMs: number): Promise<string> {
  let output = '';
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`dev server never printed ${pattern}:\n${output}`)), timeoutMs);
    child.stderr?.on('data', (chunk: Buffer) => {
      output += chunk.toString();
      if (pattern.test(output)) {
        clearTimeout(timer);
        resolve(output);
      }
    });
  });
}

test('the dev script runs the TypeScript start-up checks and refuses to start without the event store', async () => {
  const port = await freePort();
  // The source has no in-memory store (ADR-0015 decision f), so NODE_ENV=test does not help.
  const { RUNEFOBLE_DATABASE_URL: _unset, ...inherited } = process.env;
  const child = spawn('pnpm', ['run', 'dev'], {
    cwd: PACKAGE_ROOT,
    detached: true,
    stdio: ['ignore', 'ignore', 'pipe'],
    env: {
      ...inherited,
      NODE_ENV: 'test',
      PORT: String(port),
      HOST: '127.0.0.1',
      RUNEFOBLE_REDIS_URL: 'redis://127.0.0.1:1/0',
      RUNEFOBLE_ZITADEL_ISSUER: 'http://zitadel.test',
      RUNEFOBLE_ZITADEL_AUDIENCE: 'runefoble-api',
      RUNEFOBLE_SPICEDB_ENDPOINT: '127.0.0.1:50051',
      RUNEFOBLE_SPICEDB_PRESHARED_KEY: 'test-only',
    },
  });
  children.push(child);

  const stderr = await waitForStderr(child, /RUNEFOBLE_DATABASE_URL is not set/, 60_000);
  assert.match(stderr, /src\/config\.ts/);
  const health = await fetch(`http://127.0.0.1:${port}/healthz`).then(
    () => 'answered',
    () => 'refused'
  );
  assert.equal(health, 'refused');
});
