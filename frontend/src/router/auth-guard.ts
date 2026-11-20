/**
 * Runefoble SPA Router Authentication Guard
 * Enforces Zitadel OIDC authentication across protected SPA routes.
 * ADR-0004, ADR-0005, ADR-0013, ADR-0023, TASK-0214, TASK-0950, US-0062, US-0066
 */

import { router as defaultRouter, Router, JOIN_ROUTE_PATTERN } from './router.ts';
import { authService as defaultAuth, AuthService } from '../auth/auth-service.ts';
import { browserSessionStore, savePostSignInPath, type PathStore } from '../app/post-sign-in-path.ts';

export const DEFAULT_PUBLIC_ROUTES = ['#/login', '#/register'] as const;

/**
 * Registers an authentication guard on the provided router instance.
 * Automatically intercepts navigation to protected routes when unauthenticated,
 * and triggers immediate redirection to #/login if the user session terminates.
 * The join route is open to a signed-out visitor. It keeps its path for the sign-in callback.
 */
export function registerAuthGuard(
  targetRouter: Router = defaultRouter,
  auth: AuthService = defaultAuth,
  publicRoutes: readonly string[] = DEFAULT_PUBLIC_ROUTES,
  pathStore: () => PathStore = browserSessionStore
): () => void {
  const isPublic = (route: { path: string; pattern: string }) => route.pattern === JOIN_ROUTE_PATTERN || publicRoutes.includes(route.path);

  const unlistenGuard = targetRouter.beforeEach((to) => {
    if (auth.isAuthenticated()) return true;
    if (to.pattern === JOIN_ROUTE_PATTERN) {
      savePostSignInPath(pathStore(), to.path);
      return true;
    }
    return publicRoutes.includes(to.path) ? true : '#/login';
  });

  const unlistenAuth = auth.onAuthChanged((state) => {
    if (!state.isAuthenticated) {
      const current = targetRouter.getCurrentRoute();
      if (current && !isPublic(current)) {
        targetRouter.navigate('#/login');
      }
    }
  });

  return () => {
    unlistenGuard();
    unlistenAuth();
  };
}
