/**
 * Tests for the SpiceDB gRPC client (TASK-0554). The endpoint forms are parsed as documented.
 * A closed port stands in for an unreachable SpiceDB, so the client's real error mapping runs.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { v1 } from '@authzed/authzed-node';
import { DependencyUnavailableError } from '../src/errors.js';
import { createSpiceDbClient, parseSpiceDbEndpoint } from '../src/spicedb/spicedbClient.js';

test('host:port and grpc:// use plaintext gRPC, https:// uses TLS', () => {
  assert.deepEqual(parseSpiceDbEndpoint('spicedb:50051'), {
    address: 'spicedb:50051',
    security: v1.ClientSecurity.INSECURE_PLAINTEXT_CREDENTIALS,
  });
  assert.deepEqual(parseSpiceDbEndpoint('grpc://spicedb:50051'), {
    address: 'spicedb:50051',
    security: v1.ClientSecurity.INSECURE_PLAINTEXT_CREDENTIALS,
  });
  assert.deepEqual(parseSpiceDbEndpoint('https://spicedb.example:443'), {
    address: 'spicedb.example:443',
    security: v1.ClientSecurity.SECURE,
  });
});

test('other schemes and endpoints without a port are refused at start-up', () => {
  assert.throws(() => parseSpiceDbEndpoint('http://spicedb:8080'), /unsupported scheme/);
  assert.throws(() => parseSpiceDbEndpoint('spicedb'), /host:port/);
});

test('an unreachable SpiceDB surfaces as DependencyUnavailableError, not a denial', async () => {
  const client = createSpiceDbClient({ endpoint: '127.0.0.1:9', presharedKey: 'test-only', deadlineMs: 1000 });
  await assert.rejects(
    client.checkPermission({
      resource: { objectType: 'campaign', objectId: 'camp-down' },
      permission: 'view',
      subject: { objectType: 'user', objectId: 'someone' },
    }),
    DependencyUnavailableError
  );
});
