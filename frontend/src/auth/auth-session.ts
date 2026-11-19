/**
 * In-memory App Shell session: state, change listeners, and the access-token renewal timer (TASK-0871).
 * ADR-0015. The session writes through token-store.ts and never talks to Zitadel itself.
 */

import { parseJwtPayload, type UserClaims } from './claims.ts';
import type { OidcTokenResponse } from './oidc-client.ts';
import { loadStoredSession, removeStoredSession, saveStoredSession, type AuthTokens } from './token-store.ts';

export interface AuthState {
  isAuthenticated: boolean;
  user: UserClaims | null;
  tokens: AuthTokens | null;
}

export type AuthListener = (state: AuthState) => void;

/** Expiry comes from the access token `exp` claim when it is a JWT, else from `expires_in`. */
function expiresAtFor(response: OidcTokenResponse): number {
  const exp = parseJwtPayload(response.access_token)?.exp;
  if (typeof exp === 'number') return exp * 1000;
  if (typeof response.expires_in !== 'number' || !Number.isFinite(response.expires_in)) {
    throw new Error('Token response has no expiry.');
  }
  return Date.now() + response.expires_in * 1000;
}

export function toAuthTokens(response: OidcTokenResponse): AuthTokens {
  return {
    accessToken: response.access_token,
    idToken: response.id_token,
    refreshToken: response.refresh_token,
    expiresAt: expiresAtFor(response),
  };
}

export class AuthSession {
  private state: AuthState = { isAuthenticated: false, user: null, tokens: null };
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly listeners: Set<AuthListener> = new Set();
  private readonly renew: () => void;

  /** `renew` starts a token renewal. The caller owns its failure handling. */
  constructor(renew: () => void) {
    this.renew = renew;
  }

  getState(): AuthState { return { ...this.state }; }

  onChanged(listener: AuthListener): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  /** Holds the session in memory, saves it to storage, and schedules the renewal. */
  save(tokens: AuthTokens, user: UserClaims): void {
    this.state = { isAuthenticated: true, user, tokens };
    saveStoredSession(tokens, user);
    this.scheduleRefresh(tokens.expiresAt);
    this.notify();
  }

  /** Clears the timer, the memory state and the stored record. */
  clear(): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    this.refreshTimer = null;
    this.state = { isAuthenticated: false, user: null, tokens: null };
    removeStoredSession();
    this.notify();
  }

  /** Loads a stored session at start. An expired one starts a renewal. A record that cannot be read is cleared. */
  restore(): void {
    try {
      const data = loadStoredSession();
      if (!data) return;
      this.state = { isAuthenticated: true, user: data.user, tokens: data.tokens };
      if (data.tokens.expiresAt <= Date.now()) {
        // The renewal clears the session when it fails. The auth guard then sends the user to login.
        this.renew();
        return;
      }
      this.scheduleRefresh(data.tokens.expiresAt);
    } catch { this.clear(); }
  }

  private notify(): void {
    const current = this.getState();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('rf-auth-changed', { detail: current, bubbles: true, composed: true }));
    }
    for (const l of this.listeners) l(current);
  }

  private scheduleRefresh(expiresAt: number): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    const delay = Math.max(5000, expiresAt - Date.now() - 60000);
    this.refreshTimer = setTimeout(() => this.renew(), delay);
    (this.refreshTimer as any)?.unref?.();
  }
}
