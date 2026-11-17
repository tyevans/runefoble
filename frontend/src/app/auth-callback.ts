/**
 * Completes the Zitadel sign-in at /auth/callback (TASK-0524).
 * Returns an error message for the sign-in gate, or an empty string on success.
 */

import { authService } from '../auth/auth-service.ts';

export async function completeSignInCallback(): Promise<string> {
  try {
    await authService.completeSignIn(window.location.search);
    window.history.replaceState(null, '', '/#/campaigns');
    return '';
  } catch (err) {
    // The code and state leave the URL in every case. The sign-in gate shows the reason.
    window.history.replaceState(null, '', '/#/login');
    return err instanceof Error ? err.message : 'Sign-in failed.';
  }
}
