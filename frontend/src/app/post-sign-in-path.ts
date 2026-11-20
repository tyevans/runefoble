/**
 * Keeps the join route across Zitadel sign-in (ADR-0023 e, TASK-0950).
 *
 * A signed-out visitor who opens `#/join/<token>` keeps that route path in sessionStorage.
 * The key holds a route path only. It holds no credential. The sign-in callback opens the path
 * once and removes the key.
 */

export const POST_SIGN_IN_PATH_KEY = 'runefoble.postSignInPath';

/** The part of the browser storage that this module needs. */
export interface PathStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

const JOIN_PATH = /^#\/join\/[^/?#]+$/;

export function isJoinRoutePath(path: string): boolean {
  return JOIN_PATH.test(path);
}

/** Stores a join path. Any other path is ignored, so the key never holds a different route. */
export function savePostSignInPath(store: PathStore, path: string): void {
  if (isJoinRoutePath(path)) store.setItem(POST_SIGN_IN_PATH_KEY, path);
}

/** Reads and removes the stored join path. Returns null when none is stored or the stored value is not a join path. */
export function takePostSignInPath(store: PathStore): string | null {
  const stored = store.getItem(POST_SIGN_IN_PATH_KEY);
  store.removeItem(POST_SIGN_IN_PATH_KEY);
  return stored !== null && isJoinRoutePath(stored) ? stored : null;
}

/** The browser session storage. It is read only when a step needs it, so tests can run without a browser. */
export function browserSessionStore(): PathStore {
  return window.sessionStorage;
}
