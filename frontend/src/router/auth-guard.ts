/**
 * Runefoble SPA Router Authentication Guard
 * Enforces Zitadel OIDC authentication across protected SPA routes.
 * ADR-0004, ADR-0005, ADR-0013, TASK-0214, US-0062, US-0066
 */

import { router as defaultRouter, Router } from './router.ts';
import { authService as defaultAuth, AuthService } from '../auth/auth-service.ts';

export const DEFAULT_PUBLIC_ROUTES = ['#/login', '#/register'] as const;

/**
 * Registers an authentication guard on the provided router instance.
 * Automatically intercepts navigation to protected routes when unauthenticated,
 * and triggers immediate redirection to #/login if the user session terminates.
 */
export function registerAuthGuard(
  targetRouter: Router = defaultRouter,
  auth: AuthService = defaultAuth,
  publicRoutes: readonly string[] = DEFAULT_PUBLIC_ROUTES
): () => void {
  const unlistenGuard = targetRouter.beforeEach((to) => {
    if (!auth.isAuthenticated() && !publicRoutes.includes(to.path)) {
      return '#/login';
    }
    return true;
  });

  const unlistenAuth = auth.onAuthChanged((state) => {
    if (!state.isAuthenticated) {
      const current = targetRouter.getCurrentRoute()?.path;
      if (current && !publicRoutes.includes(current)) {
        targetRouter.navigate('#/login');
      }
    }
  });

  return () => {
    unlistenGuard();
    unlistenAuth();
  };
}
