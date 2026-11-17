/**
 * Runtime settings for the App Shell, served as /runtime-config.json.
 * Rendered from Helm values by TASK-0526. Holds no secret.
 */

export interface RuntimeConfig {
  issuer: string;
  clientId: string;
  scopes: string[];
  providerName: string;
}

export const RUNTIME_CONFIG_PATH = '/runtime-config.json';

export function parseRuntimeConfig(raw: unknown): RuntimeConfig {
  if (typeof raw !== 'object' || raw === null) throw new Error('Runtime config must be a JSON object.');
  const body = raw as Record<string, unknown>;
  if (typeof body.issuer !== 'string' || body.issuer === '') throw new Error('Runtime config has no issuer.');
  if (typeof body.clientId !== 'string') throw new Error('Runtime config clientId must be a string.');
  if (!Array.isArray(body.scopes) || !body.scopes.every((s) => typeof s === 'string')) {
    throw new Error('Runtime config scopes must be a list of strings.');
  }
  if (typeof body.providerName !== 'string') throw new Error('Runtime config providerName must be a string.');
  return { issuer: body.issuer, clientId: body.clientId, scopes: body.scopes as string[], providerName: body.providerName };
}

let cached: Promise<RuntimeConfig> | null = null;

/** Loads the runtime config once per page. A failed load is not cached. */
export function loadRuntimeConfig(): Promise<RuntimeConfig> {
  if (!cached) {
    cached = (async () => {
      const res = await globalThis.fetch(RUNTIME_CONFIG_PATH, { cache: 'no-store' });
      if (!res.ok) throw new Error(`Runtime config unavailable (${res.status}).`);
      const config = parseRuntimeConfig(await res.json());
      if (config.clientId === '') throw new Error('Zitadel client ID is not configured. Run the identity bootstrap first.');
      return config;
    })();
    cached.catch(() => { cached = null; });
  }
  return cached;
}
