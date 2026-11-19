/**
 * Test support (TASK-0758): a real HTTP upstream on the loopback interface.
 *
 * UI transport tests send real requests to this server instead of replacing `fetch`.
 * The server records each request and answers with the reply that the test sets.
 * It answers CORS preflights, so a browser page on another origin can call it.
 * Node only. Do not import it from browser code.
 */

import { createServer, type IncomingHttpHeaders, type IncomingMessage } from 'node:http';
import type { AddressInfo } from 'node:net';

export interface UpstreamRequest {
  method: string;
  /** Path and query, for example `/api/v1/forge/battlemap`. */
  path: string;
  headers: IncomingHttpHeaders;
  body: string;
}

export interface UpstreamReply {
  status: number;
  body: string;
  contentType?: string;
}

export interface LoopbackUpstream {
  /** Origin of the server, for example `http://127.0.0.1:41234`. Use it as the API base. */
  readonly url: string;
  /** Every request except CORS preflights, in arrival order. */
  readonly requests: UpstreamRequest[];
  /** Sets the reply for the next requests. The default is 200 with `{}`. */
  reply(status: number, body: unknown, contentType?: string): void;
  /** Clears the recorded requests and sets the default reply. */
  reset(): void;
  close(): Promise<void>;
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE',
};

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on('data', (chunk: Buffer) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function toReply(status: number, body: unknown, contentType?: string): UpstreamReply {
  if (typeof body === 'string') return { status, body, contentType: contentType ?? 'text/plain' };
  return { status, body: JSON.stringify(body), contentType: contentType ?? 'application/json' };
}

export interface LoopbackUpstreamOptions {
  /** Lets the process exit while the server listens. Use it when no test can call `close()`. */
  unref?: boolean;
}

/** Starts the server on a free loopback port. Call `close()` when the tests end. */
export async function startLoopbackUpstream(options: LoopbackUpstreamOptions = {}): Promise<LoopbackUpstream> {
  const requests: UpstreamRequest[] = [];
  let current = toReply(200, {});
  const server = createServer(async (req, res) => {
    if (req.method === 'OPTIONS') {
      res.writeHead(204, CORS_HEADERS);
      res.end();
      return;
    }
    requests.push({ method: req.method ?? '', path: req.url ?? '', headers: req.headers, body: await readBody(req) });
    res.writeHead(current.status, { ...CORS_HEADERS, 'Content-Type': current.contentType ?? 'application/json' });
    res.end(current.body);
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  if (options.unref) server.unref();
  const { port } = server.address() as AddressInfo;
  return {
    url: `http://127.0.0.1:${port}`,
    requests,
    reply(status, body, contentType) {
      current = toReply(status, body, contentType);
    },
    reset() {
      requests.length = 0;
      current = toReply(200, {});
    },
    close() {
      return new Promise((resolve, reject) => server.close((err) => (err ? reject(err) : resolve())));
    },
  };
}
