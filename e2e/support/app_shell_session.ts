/**
 * The App Shell session as the suite reads it after a real Zitadel sign-in (TASK-0525).
 *
 * The suite never writes this value. It reads the access token that Zitadel issued during the
 * browser sign-in, and the subject that the App Shell stored for it.
 */

import type { Page } from '@playwright/test';

/** localStorage key that the App Shell uses for its session (frontend/src/auth/auth-service.ts). */
export const APP_SHELL_SESSION_KEY = 'rf_auth_session';

export interface AppShellSession {
  tokens: { accessToken: string; expiresAt: number };
  user: { user_id: string; username: string };
}

export async function readAppShellSession(page: Page): Promise<AppShellSession | null> {
  const raw = await page.evaluate((key) => window.localStorage.getItem(key), APP_SHELL_SESSION_KEY);
  if (raw === null) return null;
  return JSON.parse(raw) as AppShellSession;
}
