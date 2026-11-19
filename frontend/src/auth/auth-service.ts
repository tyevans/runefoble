/**
 * Runefoble Zitadel OIDC Browser Authentication Service
 * ADR-0004, ADR-0005, ADR-0013, ADR-0015 (d), TASK-0207, TASK-0524, TASK-0871
 *
 * The App Shell never handles a password. It sends the user to Zitadel (authorization code + PKCE),
 * receives the code at /auth/callback, and keeps only the tokens Zitadel issues.
 * Claims live in claims.ts, storage in token-store.ts, and session state and renewal in auth-session.ts.
 */

import { createPkceSession, loadPendingSignIn, clearPendingSignIn, savePendingSignIn, type KeyValueStore, type PendingSignIn } from './pkce.ts';
import { OidcClient } from './oidc-client.ts';
import { loadRuntimeConfig } from './runtime-config.ts';
import { extractClaimsFromPayload, parseJwtPayload, type UserClaims } from './claims.ts';
import { AuthSession, toAuthTokens, type AuthListener, type AuthState } from './auth-session.ts';

export type { UserClaims } from './claims.ts';
export type { AuthState, AuthListener } from './auth-session.ts';
export type { AuthTokens } from './token-store.ts';

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

export class AuthService {
  private static instance: AuthService;
  private readonly env: AuthEnvironment;
  private readonly session: AuthSession;

  constructor(env: Partial<AuthEnvironment> = {}) {
    this.env = { ...defaultEnvironment(), ...env };
    this.session = new AuthSession(() => this.renewInBackground());
    this.session.restore();
  }

  static getInstance(): AuthService {
    if (!AuthService.instance) AuthService.instance = new AuthService();
    return AuthService.instance;
  }

  getState(): AuthState { return this.session.getState(); }

  /** True only while the stored access token is unexpired by its own expiry. The server still verifies every call. */
  isAuthenticated(): boolean {
    const { isAuthenticated, tokens } = this.session.getState();
    return isAuthenticated && tokens !== null && tokens.expiresAt > Date.now();
  }

  getUser(): UserClaims | null { return this.session.getState().user; }
  getAccessToken(): string | null { return this.isAuthenticated() ? this.session.getState().tokens?.accessToken || null : null; }

  onAuthChanged(listener: AuthListener): () => void {
    return this.session.onChanged(listener);
  }

  /** Merges profile changes into the signed-in user. Fails when no user is signed in. */
  updateUser(claims: Partial<UserClaims>): void {
    const { user, tokens } = this.session.getState();
    if (!user || !tokens) throw new Error('Cannot update a user without a sign-in session.');
    this.session.save(tokens, { ...user, ...claims });
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
      this.session.save(toAuthTokens(response), user);
      return user;
    } catch (err) {
      this.session.clear();
      throw err;
    }
  }

  /** Renews the access token with the refresh token. On failure the session is cleared and the error is thrown. */
  async refreshToken(): Promise<string> {
    const { tokens: current, user } = this.session.getState();
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
      this.session.save({
        accessToken: renewed.accessToken,
        idToken: renewed.idToken ?? current.idToken,
        refreshToken: renewed.refreshToken ?? current.refreshToken,
        expiresAt: renewed.expiresAt,
      }, nextUser);
      return renewed.accessToken;
    } catch (err) {
      this.session.clear();
      throw err;
    }
  }

  /** Clears the local session without contacting Zitadel. The auth guard then sends the user to sign-in. */
  discardSession(): void {
    this.session.clear();
  }

  /** Clears local tokens, then ends the Zitadel session when an ID token is held. */
  async logout(): Promise<void> {
    const idToken = this.session.getState().tokens?.idToken;
    this.session.clear();
    if (!idToken) return;
    this.env.navigate(await this.env.oidc.endSessionUrl(idToken, this.env.postLogoutUri()));
  }

  private renewInBackground(): void {
    this.refreshToken().catch((err) => console.error('Session renewal failed', err));
  }
}

export const authService = AuthService.getInstance();
