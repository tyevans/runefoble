/**
 * Fail-loud guards for e2e setup (TASK-0650, ADR-0014).
 *
 * A step that needs a value from an earlier setup call reads it through these guards.
 * A missing value or a failed setup response stops the scenario with a clear message.
 * There is no fallback id and no "continue anyway" path.
 */

/** The part of a Playwright `APIResponse` that `assertOk` reads. */
export interface SetupResponse {
  ok(): boolean;
  status(): number;
  statusText(): string;
  text(): Promise<string>;
}

/** Returns `value`. Throws with `message` when `value` is `null`, `undefined` or an empty string. */
export function requireValue<T>(value: T | null | undefined, message: string): T {
  if (value === null || value === undefined || value === '') {
    throw new Error(message);
  }
  return value;
}

/** Throws with the status and the response body when a setup response is not OK. */
export async function assertOk(res: SetupResponse, action: string): Promise<void> {
  if (res.ok()) return;
  const body = await res.text();
  throw new Error(`${action} failed: ${res.status()} ${res.statusText()} - ${body}`);
}

/**
 * Replaces each `{name}` in a route template with the id that setup stored under `name`.
 * Feature text names the route shape. The ids come from setup replies, never from the text.
 * Throws when setup did not store a value for a placeholder.
 */
export function fillRouteTemplate(
  template: string,
  values: Record<string, string | null | undefined>
): string {
  return template.replace(/\{(\w+)\}/g, (_match, name: string) =>
    requireValue(values[name], `Route "${template}" needs "${name}", which setup did not store.`)
  );
}

/** Escapes text so that it matches literally inside a `RegExp`. */
export function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** A `RegExp` that matches exactly `text`, with surrounding white space allowed. */
export function exactText(text: string): RegExp {
  return new RegExp(`^\\s*${escapeRegExp(text)}\\s*$`);
}
