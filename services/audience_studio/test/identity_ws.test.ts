/**
 * Frontdoor tests for verified identity on the WebSocket handshake (TASK-0533, ADR-0015 decision c).
 * The handshake is refused with HTTP 401 before accept. The token travels in the
 * `runefoble.bearer.<jwt>` subprotocol, never in the query string.
 */

import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { connect, type Socket } from 'node:net';
import type { AddressInfo } from 'node:net';
import { after, before, describe, test } from 'node:test';
import type { AppContext } from '../src/server.js';
import { mintWithForeignKey, startService, TestIssuer } from './helpers.js';

let issuer: TestIssuer;
let ctx: AppContext;
let port: number;

before(async () => {
  issuer = await TestIssuer.start();
  ctx = await startService(issuer);
  await ctx.server.listen({ port: 0, host: '127.0.0.1' });
  port = (ctx.server.server.address() as AddressInfo).port;
});

after(async () => {
  // A refused upgrade can leave its server-side socket open. Close it before the server closes.
  ctx.server.server.closeAllConnections();
  await ctx.server.close();
  await issuer.close();
});

interface HandshakeOutcome {
  status: number;
  headers: Record<string, string>;
}

/** Sends a raw WebSocket upgrade request and reads the status line and headers of the reply. */
function handshake(path: string, protocols: string[]): Promise<HandshakeOutcome> {
  return new Promise((resolve, reject) => {
    const socket: Socket = connect(port, '127.0.0.1');
    let received = '';
    socket.on('connect', () => {
      socket.write(
        [
          `GET ${path} HTTP/1.1`,
          `Host: 127.0.0.1:${port}`,
          'Connection: Upgrade',
          'Upgrade: websocket',
          'Sec-WebSocket-Version: 13',
          `Sec-WebSocket-Key: ${randomBytes(16).toString('base64')}`,
          ...(protocols.length > 0 ? [`Sec-WebSocket-Protocol: ${protocols.join(', ')}`] : []),
          '',
          '',
        ].join('\r\n')
      );
    });
    socket.on('data', (chunk: Buffer) => {
      received += chunk.toString('utf8');
      const end = received.indexOf('\r\n\r\n');
      if (end === -1) return;
      socket.destroy();
      const [statusLine, ...lines] = received.slice(0, end).split('\r\n');
      const headers: Record<string, string> = {};
      for (const line of lines) {
        const colon = line.indexOf(':');
        headers[line.slice(0, colon).trim().toLowerCase()] = line.slice(colon + 1).trim();
      }
      resolve({ status: Number(statusLine.split(' ')[1]), headers });
    });
    socket.on('close', () => reject(new Error(`socket closed before a reply: ${received}`)));
    socket.on('error', reject);
  });
}

const PATH = '/ws/audience/camp-live';

describe('WebSocket handshake identity', () => {
  test('a handshake with no bearer subprotocol is refused with 401', async () => {
    const outcome = await handshake(PATH, ['runefoble.v1']);
    assert.equal(outcome.status, 401);
  });

  test('a token in the query string is not accepted', async () => {
    const token = await issuer.mint('viewer-query');
    const outcome = await handshake(`${PATH}?token=${token}`, ['runefoble.v1']);
    assert.equal(outcome.status, 401);
  });

  test('a forged bearer subprotocol is refused with 401', async () => {
    const forged = await mintWithForeignKey('mallory');
    const outcome = await handshake(PATH, ['runefoble.v1', `runefoble.bearer.${forged}`]);
    assert.equal(outcome.status, 401);
  });

  test('a valid bearer subprotocol is accepted with runefoble.v1 and never echoes the token', async () => {
    const token = await issuer.mint('viewer-ws');
    const outcome = await handshake(PATH, ['runefoble.v1', `runefoble.bearer.${token}`]);
    assert.equal(outcome.status, 101);
    assert.equal(outcome.headers['sec-websocket-protocol'], 'runefoble.v1');
    assert.ok(!JSON.stringify(outcome.headers).includes(token));
  });
});
