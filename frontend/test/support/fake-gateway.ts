/**
 * Fake gateway at the fetch boundary (TASK-0640).
 *
 * Unit tests drive AppDataService through its public methods. This helper replaces
 * globalThis.fetch, the external network boundary, with a route table keyed by
 * "METHOD /api/v1/path". The key "*" matches any request that has no exact route.
 * Unrouted requests return HTTP 500 so that a missing route fails the test instead
 * of silently yielding data.
 */

export interface GatewayRequest {
  method: string;
  path: string;
  body: unknown;
}

export interface GatewayReply {
  status?: number;
  body?: unknown;
}

export type GatewayRoute = GatewayReply | ((req: GatewayRequest) => GatewayReply);

export interface FakeGateway {
  calls: GatewayRequest[];
  restore(): void;
}

export function installFakeGateway(routes: Record<string, GatewayRoute>): FakeGateway {
  const calls: GatewayRequest[] = [];
  const original = globalThis.fetch;

  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const url = new URL(raw, 'https://gateway.test');
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined;
    const req: GatewayRequest = { method, path: url.pathname, body };
    calls.push(req);

    const key = `${method} ${url.pathname}`;
    const route = routes[key] ?? routes['*'];
    const reply: GatewayReply = typeof route === 'function'
      ? route(req)
      : route ?? { status: 500, body: { detail: `No fake route for ${key}` } };

    const status = reply.status ?? 200;
    const nullBodyStatus = [101, 103, 204, 205, 304].includes(status);
    const text = reply.body === undefined || nullBodyStatus ? null : JSON.stringify(reply.body);
    return new Response(text, { status, headers: { 'Content-Type': 'application/json' } });
  }) as typeof fetch;

  return {
    calls,
    restore() {
      globalThis.fetch = original;
    },
  };
}
