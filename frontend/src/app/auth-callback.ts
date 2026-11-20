/**
 * Completes the Zitadel sign-in at /auth/callback (TASK-0524, ADR-0023 e).
 * Returns an error message for the sign-in gate, or an empty string on success.
 * After a successful sign-in the App Shell opens the join route that the visitor kept, if any.
 */

import { authService } from '../auth/auth-service.ts';
import { browserSessionStore, takePostSignInPath, type PathStore } from './post-sign-in-path.ts';

export async function completeSignInCallback(store: PathStore = browserSessionStore()): Promise<string> {
  const keptPath = takePostSignInPath(store);
  try {
    await authService.completeSignIn(window.location.search);
    window.history.replaceState(null, '', `/${keptPath ?? '#/campaigns'}`);
    return '';
  } catch (err) {
    // The code and state leave the URL in every case. The sign-in gate shows the reason.
    window.history.replaceState(null, '', '/#/login');
    return err instanceof Error ? err.message : 'Sign-in failed.';
  }
}
