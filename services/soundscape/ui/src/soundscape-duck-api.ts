/** Ducking request sent to the gateway. The owner holds the duck state. */
export interface DuckRequest {
  sessionId: string;
  isDucked: boolean;
  reason: string;
  /** Engaged duck lasts this long, then ends by itself. 0 holds until released. */
  durationMs: number;
}

/** Outcome of a ducking request. A failed request never reports success. */
export type DuckResult = { ok: true } | { ok: false; message: string };

export interface DuckApiContext {
  /** Gateway base URL. An empty string targets the same origin. */
  apiBase: string;
  /** Full Authorization header value, such as `Bearer <token>`. Empty sends no header. */
  authorization: string;
}

/** Fetch signature, injected so callers and tests can pass the transport. */
export type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

/** Sends `POST /api/v1/soundscape/duck` through the gateway. Never throws. */
export async function postDuck(
  ctx: DuckApiContext,
  request: DuckRequest,
  fetchImpl: FetchLike = (input, init) => globalThis.fetch(input, init)
): Promise<DuckResult> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (ctx.authorization) headers['Authorization'] = ctx.authorization;

  let res: Response;
  try {
    res = await fetchImpl(`${ctx.apiBase}/api/v1/soundscape/duck`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_id: request.sessionId,
        is_ducked: request.isDucked,
        reason: request.reason,
        duration_ms: request.durationMs,
      }),
    });
  } catch (err: unknown) {
    const reason = err instanceof Error ? err.message : String(err);
    return { ok: false, message: `Network error: ${reason}` };
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body?.detail === 'string' ? body.detail : `HTTP ${res.status}`;
    return { ok: false, message: detail };
  }
  return { ok: true };
}
