/**
 * Browser storage for the App Shell session record (TASK-0871, ADR-0015).
 * The record lives under `rf_auth_session` in localStorage. The e2e suite reads this key (TASK-0525).
 * Changing the key or the record shape breaks that suite. Token storage in localStorage is a
 * security decision that this module keeps unchanged.
 */

import type { UserClaims } from './claims.ts';

export interface AuthTokens {
  accessToken: string;
  idToken?: string;
  refreshToken?: string;
  expiresAt: number;
}

export interface StoredSession {
  tokens: AuthTokens;
  user: UserClaims;
}

export const STORAGE_KEY = 'rf_auth_session';

function browserStorage(): Storage | null {
  if (typeof window === 'undefined' || !window.localStorage) return null;
  return window.localStorage;
}

/**
 * Returns the stored session, or null when storage is absent, empty, or lacks a token or user.
 * Throws when the stored text is not JSON or the browser refuses the read.
 */
export function loadStoredSession(): StoredSession | null {
  const store = browserStorage();
  if (!store) return null;
  const raw = store.getItem(STORAGE_KEY);
  if (!raw) return null;
  const data = JSON.parse(raw);
  if (!data?.tokens?.accessToken || !data?.user) return null;
  return data as StoredSession;
}

export function saveStoredSession(tokens: AuthTokens, user: UserClaims): void {
  try {
    browserStorage()?.setItem(STORAGE_KEY, JSON.stringify({ tokens, user }));
  } catch { /* storage disabled: the session lives in memory only */ }
}

export function removeStoredSession(): void {
  try {
    browserStorage()?.removeItem(STORAGE_KEY);
  } catch { /* storage disabled */ }
}
