import { postJson, requestFailureMessage, type FetchLike } from '@runefoble/ui-core';
import type { HomebrewCreateRequest, HomebrewResponse } from './types.ts';

export interface HomebrewApiContext {
  /** Gateway base URL. Required: the caller refuses to submit without it. */
  apiBase: string;
  /** Resolves the caller's bearer headers. Empty when nobody is signed in. */
  authHeaders: () => Promise<Record<string, string>>;
}

/** The server's answer to a registration. `ok` means the server saved the rule. */
export type HomebrewResult = { ok: true; rule: HomebrewResponse } | { ok: false; message: string };

/**
 * Sends `POST /api/v1/compendium/homebrew` through the shared JSON request. Never throws.
 * A rejected request reports the server detail. A 2xx reply without a rule body is a failure.
 */
export async function postHomebrewRule(
  ctx: HomebrewApiContext,
  payload: HomebrewCreateRequest,
  fetchImpl?: FetchLike,
): Promise<HomebrewResult> {
  try {
    const rule = await postJson<HomebrewResponse | undefined>(
      `${ctx.apiBase}/api/v1/compendium/homebrew`,
      payload,
      { headers: await ctx.authHeaders(), fetchImpl },
    );
    if (!rule) return { ok: false, message: 'The server did not return the registered rule.' };
    return { ok: true, rule };
  } catch (err) {
    return { ok: false, message: requestFailureMessage(err) };
  }
}
