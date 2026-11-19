/**
 * Shared HTTP and socket helpers for every microfrontend (TASK-0825, audit F-05 and F-06).
 * TASK-0758 adds the API base, the auth source and `FormData` bodies to `request`.
 *
 * One request path: a non-2xx response throws HttpError with the server detail. A network
 * failure propagates as the fetch error. Nothing returns substitute data.
 */

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

/** A source of the caller's bearer headers. `AuthConsumerController` is one. */
export interface AuthSource {
  authHeaders(): Promise<Record<string, string>>;
}

export interface RequestOptions {
  /** API base URL put in front of the path, for example `https://gateway.example`. Empty means the page origin. */
  apiBase?: string;
  /** Bearer source. `request` reads its headers once for each call. */
  auth?: AuthSource;
  /** Extra headers. They win over the auth headers when a name is the same. */
  headers?: Record<string, string>;
  /** Transport. Defaults to the global fetch, read at call time. */
  fetchImpl?: FetchLike;
}

/** Request settings. Headers come from `RequestOptions`. The body is a JSON string or a `FormData`. */
export type RequestSpec = Omit<RequestInit, 'headers' | 'body'> & { body?: string | FormData };

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

/** The FastAPI `detail`, else the `message` of an engine-unavailable body, else the status. */
async function readErrorDetail(res: Response): Promise<string> {
  const fallback = `Request failed with status ${res.status}`;
  let parsed: unknown;
  try {
    parsed = JSON.parse(await res.text());
  } catch {
    return fallback;
  }
  const detail = errorDetailFromBody(parsed);
  if (detail) return detail;
  if (isRecord(parsed) && typeof parsed.message === 'string' && parsed.message.trim()) return parsed.message;
  return fallback;
}

/** Joins the API base and a path. A trailing slash on the base is dropped. */
export function apiUrl(apiBase: string | undefined, path: string): string {
  return `${(apiBase ?? '').replace(/\/+$/, '')}${path}`;
}

function contentTypeHeader(body: RequestSpec['body']): Record<string, string> {
  // The browser sets the multipart boundary for a FormData body. A JSON string needs the JSON type.
  return typeof body === 'string' ? { 'Content-Type': 'application/json' } : {};
}

/**
 * The one shared transport (TASK-0758). Sends `path` under `opts.apiBase` with the bearer from
 * `opts.auth`, and resolves with the parsed JSON body. An empty success body resolves with
 * undefined. A non-2xx response throws HttpError with the server detail. A network failure
 * propagates as the fetch error.
 */
export async function request<T>(path: string, spec: RequestSpec = {}, opts: RequestOptions = {}): Promise<T> {
  const fetchImpl: FetchLike = opts.fetchImpl ?? ((input, reqInit) => globalThis.fetch(input, reqInit));
  const headers: Record<string, string> = {
    ...contentTypeHeader(spec.body),
    ...(opts.auth ? await opts.auth.authHeaders() : {}),
    ...opts.headers,
  };
  const res = await fetchImpl(apiUrl(opts.apiBase, path), { ...spec, headers });
  if (!res.ok) throw new HttpError(res.status, await readErrorDetail(res));
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/** POSTs a JSON body through `request`. */
export function postJson<T>(path: string, body: unknown, opts: RequestOptions = {}): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) }, opts);
}

/** POSTs a multipart `FormData` body through `request`. */
export function postForm<T>(path: string, form: FormData, opts: RequestOptions = {}): Promise<T> {
  return request<T>(path, { method: 'POST', body: form }, opts);
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
