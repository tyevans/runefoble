/**
 * Runefoble end-to-end environment constants.
 * The suite runs against the Kind stack through the Traefik ingress (TASK-0525, ADR-0005, ADR-0014).
 */

/** Public origin of the App Shell, the gateway routes, and the Zitadel issuer. */
export const APP_BASE_URL = (process.env.PLAYWRIGHT_BASE_URL || 'http://localhost').replace(/\/$/, '');

/** Environment variable that carries the Zitadel admin personal access token into global setup. */
export const ZITADEL_ADMIN_PAT_ENV = 'ZITADEL_ADMIN_PAT';
