/**
 * Shared helpers for Audience Studio tests.
 */

export function jsonBody(res: { body: string }): any {
  return JSON.parse(res.body);
}
