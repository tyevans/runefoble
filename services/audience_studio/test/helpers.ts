/**
 * Shared helpers for Audience Studio tests.
 *
 * TestIssuer plays the Zitadel role. It serves a real JWKS document over HTTP and mints
 * RS256 tokens. The service under test fetches the keys from that URL, as in deployment.
 */

import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import type { AddressInfo } from 'node:net';
import { exportJWK, generateKeyPair, SignJWT, type CryptoKey, type JWK } from 'jose';
import { MemoryEventStore } from '../src/eventStore/memoryEventStore.js';
import { InMemoryStreamPublisher } from '../src/memoryStreams.js';
import type { AppContext } from '../src/server.js';
import { buildServer } from '../src/server.js';

export const TEST_ISSUER = 'http://zitadel.test';
export const TEST_AUDIENCE = 'runefoble-api';
const KID = 'test-key-1';

export function jsonBody(res: { body: string }): any {
  return JSON.parse(res.body);
}

export function bearer(token: string): { authorization: string } {
  return { authorization: `Bearer ${token}` };
}

export interface MintOptions {
  audience?: string;
  issuer?: string;
  expiresInSeconds?: number;
}

export class TestIssuer {
  private constructor(
    private readonly privateKey: CryptoKey,
    private readonly jwk: JWK,
    private readonly server: Server,
    /** URL that the service under test reads its signing keys from. */
    readonly jwksUrl: string
  ) {}

  static async start(): Promise<TestIssuer> {
    const { privateKey, publicKey } = await generateKeyPair('RS256');
    const jwk = { ...(await exportJWK(publicKey)), kid: KID, alg: 'RS256', use: 'sig' };
    const body = JSON.stringify({ keys: [jwk] });
    const server = createServer((req: IncomingMessage, res: ServerResponse) => {
      if (req.url === '/keys') {
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end(body);
        return;
      }
      res.writeHead(404).end();
    });
    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
    const { port } = server.address() as AddressInfo;
    return new TestIssuer(privateKey, jwk, server, `http://127.0.0.1:${port}/keys`);
  }

  async close(): Promise<void> {
    // Keep-alive sockets from the verifier would hold the server open. Drop them first.
    this.server.closeAllConnections();
    await new Promise<void>((resolve, reject) =>
      this.server.close((err) => (err ? reject(err) : resolve()))
    );
  }

  /** Mints a token that Zitadel would accept for `sub`. Overrides build negative cases. */
  async mint(sub: string, options: MintOptions = {}): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    return new SignJWT({ preferred_username: `${sub}-name`, email: `${sub}@runefoble.local` })
      .setProtectedHeader({ alg: 'RS256', kid: KID })
      .setSubject(sub)
      .setIssuer(options.issuer ?? TEST_ISSUER)
      .setAudience(options.audience ?? TEST_AUDIENCE)
      .setIssuedAt(now)
      .setExpirationTime(now + (options.expiresInSeconds ?? 3600))
      .sign(this.privateKey);
  }
}

/** A token signed by a key that the service does not trust. */
export async function mintWithForeignKey(sub: string): Promise<string> {
  const { privateKey } = await generateKeyPair('RS256');
  return new SignJWT({})
    .setProtectedHeader({ alg: 'RS256', kid: KID })
    .setSubject(sub)
    .setIssuer(TEST_ISSUER)
    .setAudience(TEST_AUDIENCE)
    .setExpirationTime(Math.floor(Date.now() / 1000) + 3600)
    .sign(privateKey);
}

/** A token signed with HS256 and a shared secret. The service must reject the algorithm. */
export async function mintHs256(sub: string): Promise<string> {
  return new SignJWT({})
    .setProtectedHeader({ alg: 'HS256' })
    .setSubject(sub)
    .setIssuer(TEST_ISSUER)
    .setAudience(TEST_AUDIENCE)
    .setExpirationTime(Math.floor(Date.now() / 1000) + 3600)
    .sign(new TextEncoder().encode('a-shared-secret-that-is-at-least-32-bytes'));
}

/** An unsigned token with `alg: none`. */
export function mintAlgNone(sub: string): string {
  const encode = (value: object) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const payload = {
    sub,
    iss: TEST_ISSUER,
    aud: TEST_AUDIENCE,
    exp: Math.floor(Date.now() / 1000) + 3600,
  };
  return `${encode({ alg: 'none' })}.${encode(payload)}.`;
}

/** Builds a server that trusts the given issuer. Stores and streams are in memory (tests only). */
export async function startService(issuer: TestIssuer, jwksUrl = issuer.jwksUrl): Promise<AppContext> {
  return buildServer({
    spicedbToken: '',
    logger: false,
    zitadel: { issuer: TEST_ISSUER, audience: TEST_AUDIENCE, jwksUrl },
    createAdapters: async () => ({
      eventStore: new MemoryEventStore(),
      streamPublisher: new InMemoryStreamPublisher(),
    }),
  });
}
