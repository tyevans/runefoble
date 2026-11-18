/**
 * Shared HTTP and socket helpers for every microfrontend (TASK-0825, audit F-05 and F-06).
 *
 * One request path: a non-2xx response throws HttpError with the server detail. A network
 * failure propagates as the fetch error. Nothing returns substitute data.
 */

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface RequestOptions {
  /** Extra headers, such as the bearer from `AuthConsumerController.authHeaders()`. */
  headers?: Record<string, string>;
  /** Transport. Defaults to the global fetch, read at call time. */
  fetchImpl?: FetchLike;
}

/** Outcome of a write that reports to the user and never throws. */
export type ActionResult = { ok: true } | { ok: false; message: string };

/** A non-2xx response. `detail` is the server message, or a status message when none exists. */
export class HttpError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'HttpError';
    this.status = status;
    this.detail = detail;
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/** Returns `{ Authorization: 'Bearer ...' }` for a token, else an empty object. */
export function bearerHeaders(token: string | null | undefined): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Reads the server message from a FastAPI-style body: a `detail` string, or joined `detail[].msg`. */
export function errorDetailFromBody(body: unknown): string | undefined {
  if (!isRecord(body)) return undefined;
  const detail = body.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => (isRecord(item) && typeof item.msg === 'string' ? item.msg : ''))
      .filter(Boolean);
    if (parts.length > 0) return parts.join('; ');
  }
  return undefined;
}

/** Pulls a human-readable message from an error body, or falls back to the status code. */
export function errorMessageFromBody(body: unknown, status: number): string {
  const detail = errorDetailFromBody(body);
  if (detail) return detail;
  if (isRecord(body)) {
    if (typeof body.message === 'string' && body.message.trim()) return body.message;
    if (typeof body.error === 'string' && body.error.trim()) return body.error;
  }
  return status === 404 ? 'The requested item was not found.' : `The request failed with status ${status}.`;
}

async function readErrorDetail(res: Response): Promise<string> {
  const text = await res.text().catch(() => '');
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return `Request failed with status ${res.status}`;
  }
  return errorDetailFromBody(parsed) ?? `Request failed with status ${res.status}`;
}

/**
 * Sends a request and resolves with the parsed JSON body. An empty success body resolves
 * with undefined. A non-2xx response throws HttpError.
 */
export async function requestJson<T>(
  url: string,
  init: RequestInit = {},
  opts: RequestOptions = {},
): Promise<T> {
  const fetchImpl: FetchLike = opts.fetchImpl ?? ((input, reqInit) => globalThis.fetch(input, reqInit));
  const headers: Record<string, string> = {
    ...(init.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    ...opts.headers,
  };
  const res = await fetchImpl(url, { ...init, headers });
  if (!res.ok) throw new HttpError(res.status, await readErrorDetail(res));
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/** POSTs a JSON body through requestJson. */
export function postJson<T>(url: string, body: unknown, opts: RequestOptions = {}): Promise<T> {
  return requestJson<T>(url, { method: 'POST', body: JSON.stringify(body) }, opts);
}

/** The user-facing message for a failed request: the server detail, or a network note. */
export function requestFailureMessage(err: unknown): string {
  if (err instanceof HttpError) return err.detail;
  const reason = err instanceof Error ? err.message : String(err);
  return `Network error: ${reason}`;
}

/**
 * WebSocket URL on the page origin for a path. `https:` pages use `wss:`, others `ws:`.
 * Pass `loc` to build the URL for another origin.
 */
export function wsUrl(path: string, loc: Pick<Location, 'protocol' | 'host'> = window.location): string {
  const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${loc.host}${path}`;
}
