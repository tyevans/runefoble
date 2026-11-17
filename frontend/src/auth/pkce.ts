/**
 * PKCE helpers for the OIDC authorization-code flow (RFC 7636).
 * TASK-0524, ADR-0015 (d): sign-in uses Zitadel with PKCE. No password is handled in the App Shell.
 */

export interface PkceSession {
  state: string;
  nonce: string;
  codeVerifier: string;
  codeChallenge: string;
}

export interface PendingSignIn {
  state: string;
  nonce: string;
  codeVerifier: string;
}

export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export const PENDING_SIGN_IN_KEY = 'rf_oidc_pending';

/** Encodes bytes as unpadded base64url (RFC 4648 section 5). */
export function base64UrlEncode(bytes: Uint8Array): string {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** Returns a random URL-safe string built from `byteLength` cryptographic random bytes. */
export function randomToken(byteLength = 32): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

/** S256 code challenge: BASE64URL(SHA256(ASCII(code_verifier))). */
export async function s256Challenge(codeVerifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(codeVerifier));
  return base64UrlEncode(new Uint8Array(digest));
}

/** Creates the verifier, challenge, state, and nonce for one sign-in attempt. 32 bytes give a 43-character verifier. */
export async function createPkceSession(): Promise<PkceSession> {
  const codeVerifier = randomToken(32);
  return {
    state: randomToken(16),
    nonce: randomToken(16),
    codeVerifier,
    codeChallenge: await s256Challenge(codeVerifier),
  };
}

export function savePendingSignIn(store: KeyValueStore, pending: PendingSignIn): void {
  store.setItem(PENDING_SIGN_IN_KEY, JSON.stringify(pending));
}

/** Reads and validates the pending sign-in. Returns null when none is stored or the stored value is malformed. */
export function loadPendingSignIn(store: KeyValueStore): PendingSignIn | null {
  const raw = store.getItem(PENDING_SIGN_IN_KEY);
  if (!raw) return null;
  const parsed = JSON.parse(raw) as Partial<PendingSignIn>;
  if (typeof parsed.state !== 'string' || typeof parsed.nonce !== 'string' || typeof parsed.codeVerifier !== 'string') {
    throw new Error('Stored sign-in data is malformed. Start sign-in again.');
  }
  return { state: parsed.state, nonce: parsed.nonce, codeVerifier: parsed.codeVerifier };
}

export function clearPendingSignIn(store: KeyValueStore): void {
  store.removeItem(PENDING_SIGN_IN_KEY);
}
