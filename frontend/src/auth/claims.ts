/**
 * JWT payload decoding and claim extraction for the App Shell (TASK-0871, ADR-0015).
 * Pure functions. They read token text and never verify a signature. The server verifies every call.
 */

export interface UserClaims {
  user_id: string;
  username: string;
  email?: string;
  roles: string[];
  display_name?: string;
  avatar_url?: string;
  bio?: string;
}

export function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64).split('').map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
    );
    return JSON.parse(json);
  } catch { return null; }
}

export function extractClaimsFromPayload(payload: Record<string, unknown>): UserClaims {
  const rolesRaw = payload['urn:zitadel:iam:org:project:roles'] || payload.roles || [];
  const roles: string[] = Array.isArray(rolesRaw) ? rolesRaw.map(String) :
    typeof rolesRaw === 'object' && rolesRaw !== null ? Object.keys(rolesRaw) : [];
  const sub = String(payload.sub || payload.user_id || 'user-unknown');
  return {
    user_id: sub,
    username: String(payload.preferred_username || payload.username || payload.name || sub),
    email: payload.email ? String(payload.email) : undefined,
    roles,
    display_name: payload.display_name ? String(payload.display_name) : (payload.name ? String(payload.name) : undefined),
    avatar_url: payload.avatar_url || payload.picture ? String(payload.avatar_url || payload.picture) : undefined,
    bio: payload.bio ? String(payload.bio) : undefined,
  };
}
