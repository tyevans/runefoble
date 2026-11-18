/**
 * Runefoble Zitadel OIDC Browser Authentication Service
 * ADR-0004, ADR-0005, ADR-0013, ADR-0015 (d), TASK-0207, TASK-0524
 *
 * The App Shell never handles a password. It sends the user to Zitadel (authorization code + PKCE),
 * receives the code at /auth/callback, and keeps only the tokens Zitadel issues.
 */

import { createPkceSession, loadPendingSignIn, clearPendingSignIn, savePendingSignIn, type KeyValueStore, type PendingSignIn } from './pkce.ts';
import { OidcClient, type OidcTokenResponse } from './oidc-client.ts';
import { loadRuntimeConfig } from './runtime-config.ts';

export interface UserClaims {
  user_id: string;
  username: string;
  email?: string;
  roles: string[];
  display_name?: string;
  avatar_url?: string;
  bio?: string;
}

export interface AuthTokens {
  accessToken: string;
  idToken?: string;
  refreshToken?: string;
  expiresAt: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: UserClaims | null;
  tokens: AuthTokens | null;
}

export type AuthListener = (state: AuthState) => void;
const STORAGE_KEY = 'rf_auth_session';

/** Path that receives the Zitadel redirect. A redirect URI cannot carry a fragment, so this is a real path, not a hash route. */
export const AUTH_CALLBACK_PATH = '/auth/callback';

export function isAuthCallbackPath(pathname: string): boolean {
  return pathname === AUTH_CALLBACK_PATH;
}

/** Browser-side wiring. Tests inject fakes for each field. */
export interface AuthEnvironment {
  oidc: OidcClient;
  callbackUri: () => string;
  postLogoutUri: () => string;
  navigate: (url: string) => void;
  pendingStore: () => KeyValueStore;
}

function defaultEnvironment(): AuthEnvironment {
  return {
    oidc: new OidcClient(loadRuntimeConfig, (input, init) => globalThis.fetch(input, init)),
    callbackUri: () => `${window.location.origin}${AUTH_CALLBACK_PATH}`,
    postLogoutUri: () => `${window.location.origin}/`,
    navigate: (url) => window.location.assign(url),
    pendingStore: () => window.sessionStorage,
  };
}

export function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64).split('').map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
    );
    return JSON.parse(json);
  } catch { return null; }
}

export function extractClaimsFromPayload(payload: Record<string, unknown>): UserClaims {
  const rolesRaw = payload['urn:zitadel:iam:org:project:roles'] || payload.roles || [];
  const roles: string[] = Array.isArray(rolesRaw) ? rolesRaw.map(String) :
    typeof rolesRaw === 'object' && rolesRaw !== null ? Object.keys(rolesRaw) : [];
  const sub = String(payload.sub || payload.user_id || 'user-unknown');
  return {
    user_id: sub,
    username: String(payload.preferred_username || payload.username || payload.name || sub),
    email: payload.email ? String(payload.email) : undefined,
    roles,
    display_name: payload.display_name ? String(payload.display_name) : (payload.name ? String(payload.name) : undefined),
    avatar_url: payload.avatar_url || payload.picture ? String(payload.avatar_url || payload.picture) : undefined,
    bio: payload.bio ? String(payload.bio) : undefined,
  };
}

/** Expiry comes from the access token `exp` claim when it is a JWT, else from `expires_in`. */
function expiresAtFor(response: OidcTokenResponse): number {
  const exp = parseJwtPayload(response.access_token)?.exp;
  if (typeof exp === 'number') return exp * 1000;
  if (typeof response.expires_in !== 'number' || !Number.isFinite(response.expires_in)) {
    throw new Error('Token response has no expiry.');
  }
  return Date.now() + response.expires_in * 1000;
}

function toAuthTokens(response: OidcTokenResponse): AuthTokens {
  return {
    accessToken: response.access_token,
    idToken: response.id_token,
    refreshToken: response.refresh_token,
    expiresAt: expiresAtFor(response),
  };
}

export class AuthService {
  private static instance: AuthService;
  private state: AuthState = { isAuthenticated: false, user: null, tokens: null };
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Set<AuthListener> = new Set();
  private readonly env: AuthEnvironment;

  constructor(env: Partial<AuthEnvironment> = {}) {
    this.env = { ...defaultEnvironment(), ...env };
    this.restoreSession();
  }

  static getInstance(): AuthService {
    if (!AuthService.instance) AuthService.instance = new AuthService();
    return AuthService.instance;
  }

  getState(): AuthState { return { ...this.state }; }

  /** True only while the stored access token is unexpired by its own expiry. The server still verifies every call. */
  isAuthenticated(): boolean {
    return this.state.isAuthenticated && this.state.tokens !== null && this.state.tokens.expiresAt > Date.now();
  }

  getUser(): UserClaims | null { return this.state.user; }
  getAccessToken(): string | null { return this.isAuthenticated() ? this.state.tokens?.accessToken || null : null; }

  onAuthChanged(listener: AuthListener): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  /** Merges profile changes into the signed-in user. Fails when no user is signed in. */
  updateUser(claims: Partial<UserClaims>): void {
    if (!this.state.user || !this.state.tokens) throw new Error('Cannot update a user without a sign-in session.');
    this.persistSession(this.state.tokens, { ...this.state.user, ...claims });
  }

  /** Redirects the browser to Zitadel. `signUp` opens the hosted registration page. */
  async startSignIn(options: { signUp?: boolean } = {}): Promise<void> {
    const pkce = await createPkceSession();
    const store = this.env.pendingStore();
    savePendingSignIn(store, { state: pkce.state, nonce: pkce.nonce, codeVerifier: pkce.codeVerifier });
    try {
      const url = await this.env.oidc.buildAuthorizeUrl({
        state: pkce.state,
        nonce: pkce.nonce,
        codeChallenge: pkce.codeChallenge,
        redirectUri: this.env.callbackUri(),
        signUp: options.signUp === true,
      });
      this.env.navigate(url);
    } catch (err) {
      clearPendingSignIn(store);
      throw err;
    }
  }

  /**
   * Finishes the sign-in at /auth/callback. Checks `state` and `nonce`, exchanges the code with the PKCE verifier,
   * and stores the tokens. On any error the session is cleared and the error is thrown.
   */
  async completeSignIn(search: string): Promise<UserClaims> {
    const store = this.env.pendingStore();
    try {
      const params = new URLSearchParams(search);
      let pending: PendingSignIn | null;
      try {
        pending = loadPendingSignIn(store);
      } finally {
        clearPendingSignIn(store);
      }
      const oidcError = params.get('error');
      if (oidcError) throw new Error(`Sign-in was not completed (${oidcError}).`);
      if (!pending) throw new Error('No sign-in is pending. Start sign-in again.');
      if (params.get('state') !== pending.state) throw new Error('Sign-in state did not match. No session was stored.');
      const code = params.get('code');
      if (!code) throw new Error('Sign-in response has no authorization code.');

      const response = await this.env.oidc.exchangeCode({
        code,
        codeVerifier: pending.codeVerifier,
        redirectUri: this.env.callbackUri(),
      });
      if (!response.id_token) throw new Error('Token response has no ID token.');
      const idClaims = parseJwtPayload(response.id_token);
      if (!idClaims || idClaims.nonce !== pending.nonce) throw new Error('Sign-in nonce did not match. No session was stored.');

      const user = extractClaimsFromPayload(idClaims);
      this.persistSession(toAuthTokens(response), user);
      return user;
    } catch (err) {
      this.clearSession();
      throw err;
    }
  }

  /** Renews the access token with the refresh token. On failure the session is cleared and the error is thrown. */
  async refreshToken(): Promise<string> {
    const current = this.state.tokens;
    const user = this.state.user;
    try {
      if (!current?.refreshToken || !user) throw new Error('No refresh token available');
      const response = await this.env.oidc.refresh(current.refreshToken);
      let nextUser = user;
      if (response.id_token) {
        const claims = parseJwtPayload(response.id_token);
        if (!claims) throw new Error('Refreshed ID token is malformed.');
        nextUser = extractClaimsFromPayload(claims);
        if (nextUser.user_id !== user.user_id) throw new Error('Refreshed token belongs to another user.');
      }
      const renewed = toAuthTokens(response);
      this.persistSession({
        accessToken: renewed.accessToken,
        idToken: renewed.idToken ?? current.idToken,
        refreshToken: renewed.refreshToken ?? current.refreshToken,
        expiresAt: renewed.expiresAt,
      }, nextUser);
      return renewed.accessToken;
    } catch (err) {
      this.clearSession();
      throw err;
    }
  }

  /** Clears the local session without contacting Zitadel. The auth guard then sends the user to sign-in. */
  discardSession(): void {
    this.clearSession();
  }

  /** Clears local tokens, then ends the Zitadel session when an ID token is held. */
  async logout(): Promise<void> {
    const idToken = this.state.tokens?.idToken;
    this.clearSession();
    if (!idToken) return;
    this.env.navigate(await this.env.oidc.endSessionUrl(idToken, this.env.postLogoutUri()));
  }

  private notify(): void {
    const current = this.getState();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('rf-auth-changed', { detail: current, bubbles: true, composed: true }));
    }
    for (const l of this.listeners) l(current);
  }

  private persistSession(tokens: AuthTokens, user: UserClaims): void {
    this.state = { isAuthenticated: true, user, tokens };
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ tokens, user }));
      }
    } catch { /* storage disabled */ }
    this.scheduleRefresh(tokens.expiresAt);
    this.notify();
  }

  private clearSession(): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    this.refreshTimer = null;
    this.state = { isAuthenticated: false, user: null, tokens: null };
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch { /* storage disabled */ }
    this.notify();
  }

  private restoreSession(): void {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return;
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data?.tokens?.accessToken || !data?.user) return;
      this.state = { isAuthenticated: true, user: data.user, tokens: data.tokens };
      if (data.tokens.expiresAt <= Date.now()) {
        // refreshToken() clears the session when renewal fails. The guard then sends the user to login.
        this.refreshToken().catch((err) => console.error('Session renewal failed', err));
        return;
      }
      this.scheduleRefresh(data.tokens.expiresAt);
    } catch { this.clearSession(); }
  }

  private scheduleRefresh(expiresAt: number): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    const delay = Math.max(5000, expiresAt - Date.now() - 60000);
    this.refreshTimer = setTimeout(() => {
      this.refreshToken().catch((err) => console.error('Session renewal failed', err));
    }, delay);
    (this.refreshTimer as any)?.unref?.();
  }
}

export const authService = AuthService.getInstance();
