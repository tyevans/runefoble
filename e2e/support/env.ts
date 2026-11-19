/**
 * Runefoble end-to-end environment values (TASK-0525, TASK-0875, ADR-0005, ADR-0014).
 *
 * This is the only module under e2e/support that reads process.env for the suite. Every default value lives here.
 * The suite runs against the Kind stack through the Traefik ingress.
 */

/**
 * Public origin of the gateway API and the App Shell. Both are served by one ingress, so one value covers both.
 * Set PLAYWRIGHT_BASE_URL to point the suite at another origin.
 */
export const API_BASE_URL = (process.env.PLAYWRIGHT_BASE_URL || 'http://localhost').replace(/\/$/, '');

/** Zitadel issuer that the forged-token negative scenarios name. Set PLAYWRIGHT_ZITADEL_ISSUER to override. */
export const ZITADEL_ISSUER = process.env.PLAYWRIGHT_ZITADEL_ISSUER || 'http://auth.localhost';

/** Zitadel audience that the forged-token negative scenarios name. Set PLAYWRIGHT_ZITADEL_AUDIENCE to override. */
export const ZITADEL_AUDIENCE = process.env.PLAYWRIGHT_ZITADEL_AUDIENCE || 'runefoble-api';

/** Environment variable that carries the Zitadel admin personal access token into global setup. */
export const ZITADEL_ADMIN_PAT_ENV = 'ZITADEL_ADMIN_PAT';
