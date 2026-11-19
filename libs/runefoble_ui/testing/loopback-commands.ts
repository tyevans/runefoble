/**
 * Vitest browser commands for the loopback upstream (TASK-0758).
 *
 * A browser test cannot open a server. These commands run in the Vitest Node process. They
 * start one loopback upstream for the run, set its reply and read what it received. Pass them
 * to `domTestConfig(dir, { commands: loopbackUpstreamCommands })`. In the test, call them with
 * `commands` from `vitest/browser`.
 */

import type { BrowserCommand } from 'vitest/node';
import { startLoopbackUpstream, type LoopbackUpstream } from './loopback-upstream.ts';

/** A received request, in a form that can cross from Node to the browser. */
export interface ReceivedRequest {
  method: string;
  path: string;
  authorization: string | null;
  contentType: string | null;
  body: string;
}

let upstream: Promise<LoopbackUpstream> | undefined;

function shared(): Promise<LoopbackUpstream> {
  upstream ??= startLoopbackUpstream({ unref: true });
  return upstream;
}

const upstreamUrl: BrowserCommand<[]> = async () => (await shared()).url;

const upstreamReply: BrowserCommand<[status: number, body: unknown]> = async (_ctx, status, body) => {
  (await shared()).reply(status, body);
};

const upstreamReset: BrowserCommand<[]> = async () => {
  (await shared()).reset();
};

const upstreamRequests: BrowserCommand<[]> = async (): Promise<ReceivedRequest[]> =>
  (await shared()).requests.map((req) => ({
    method: req.method,
    path: req.path,
    authorization: req.headers.authorization ?? null,
    contentType: req.headers['content-type'] ?? null,
    body: req.body,
  }));

export const loopbackUpstreamCommands = { upstreamUrl, upstreamReply, upstreamReset, upstreamRequests };
