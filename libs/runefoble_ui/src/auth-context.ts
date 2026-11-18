import { createContext } from '@lit/context';

/**
 * Auth contract between the App Shell and microfrontends.
 * The shell answers `context-request` events for the key `runefoble-auth`.
 */
export interface AuthContextValue {
  /** Resolves the current bearer token, or null when nobody is signed in. */
  getAccessToken(): Promise<string | null>;
}

export const AUTH_CONTEXT_KEY = 'runefoble-auth';

export const authContext = createContext<AuthContextValue>(AUTH_CONTEXT_KEY);
