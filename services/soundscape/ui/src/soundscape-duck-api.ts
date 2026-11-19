import { postJson, requestFailureMessage, type ActionResult, type FetchLike } from '@runefoble/ui-core';

/** Ducking request sent to the gateway. The owner holds the duck state. */
export interface DuckRequest {
  sessionId: string;
  isDucked: boolean;
  reason: string;
  /** Engaged duck lasts this long, then ends by itself. 0 holds until released. */
  durationMs: number;
}

export interface DuckApiContext {
  /** Gateway base URL. An empty string targets the same origin. */
  apiBase: string;
  /** Resolves the caller's auth headers, such as `AuthConsumerController.authHeaders`. Empty sends no header. */
  authHeaders: () => Promise<Record<string, string>>;
}

/** Sends `POST /api/v1/soundscape/duck` through the gateway. Never throws. A failure reports the owner detail. */
export async function postDuck(
  ctx: DuckApiContext,
  request: DuckRequest,
  fetchImpl?: FetchLike
): Promise<ActionResult> {
  try {
    const headers = await ctx.authHeaders();
    await postJson(
      `${ctx.apiBase}/api/v1/soundscape/duck`,
      {
        session_id: request.sessionId,
        is_ducked: request.isDucked,
        reason: request.reason,
        duration_ms: request.durationMs,
      },
      { headers, fetchImpl }
    );
    return { ok: true };
  } catch (err) {
    return { ok: false, message: requestFailureMessage(err) };
  }
}
