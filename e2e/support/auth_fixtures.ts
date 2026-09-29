/**
 * Runefoble Frontdoor Authentication Fixtures
 * Injects valid Zitadel JWT tokens into browser localStorage without backdoor database tampering.
 * Governed by ADR-0014, ADR-0001, and Hard Invariant 7.
 */

import type { BrowserContext, Page } from '@playwright/test';
import type { TestUser } from './world';

export interface UserClaims {
  user_id: string;
  username: string;
  email?: string;
  roles: string[];
  is_admin?: boolean;
  display_name?: string;
  avatar_url?: string;
  bio?: string;
}

export const PREDEFINED_PERSONAS: Record<string, UserClaims> = {
  dm: {
    user_id: 'user-dm-eldrin',
    username: 'Dungeon Master Eldrin',
    email: 'eldrin@runefoble.dev',
    roles: ['dm', 'player'],
    is_admin: true,
    display_name: 'Dungeon Master Eldrin',
    bio: 'Keeper of ancient lore and arbiter of fates.',
  },
  player: {
    user_id: 'user-valeros',
    username: 'Valeros of Korvosa',
    email: 'valeros@runefoble.dev',
    roles: ['player'],
    is_admin: false,
    display_name: 'Valeros of Korvosa',
    bio: 'Valiant fighter defending the weak with blade and shield.',
  },
  spectator: {
    user_id: 'user-spectator-zephyr',
    username: 'Spectator Zephyr',
    email: 'zephyr@runefoble.dev',
    roles: ['spectator'],
    is_admin: false,
    display_name: 'Spectator Zephyr',
    bio: 'Tavern observer watching epic tabletop battles unfold.',
  },
  evelyn: {
    user_id: 'user-dm-evelyn',
    username: 'Evelyn',
    email: 'evelyn@runefoble.dev',
    roles: ['dm', 'player', 'owner'],
    is_admin: true,
    display_name: 'Evelyn Vance',
    bio: 'Dungeon Master orchestrating campaign adventures.',
  },
  valeros: {
    user_id: 'user-valeros',
    username: 'Valeros',
    email: 'valeros@runefoble.dev',
    roles: ['player'],
    is_admin: false,
    display_name: 'Valeros of Korvosa',
    bio: 'Valiant fighter defending the weak with blade and shield.',
  },
  sarah: {
    user_id: 'user-sarah',
    username: 'Sarah',
    email: 'sarah@runefoble.dev',
    roles: ['player'],
    is_admin: false,
    display_name: 'Sarah Shadowstep',
    bio: 'Shadow rogue navigating the ancient halls.',
  },
};

/**
 * Creates a valid 3-part base64url JWT token
 * parsable by frontend AuthService and gateway JWT validation middleware.
 */
export function createMockJwt(claims: Partial<UserClaims>): string {
  const header = {
    alg: 'RS256',
    typ: 'JWT',
    kid: 'runefoble-dev-key',
  };

  const nowSec = Math.floor(Date.now() / 1000);
  const expSec = nowSec + 86400 * 7; // 7 days

  const payload: Record<string, unknown> = {
    iss: 'https://auth.runefoble.local',
    sub: claims.user_id || 'user-valeros',
    aud: ['runefoble-client', 'runefoble-api'],
    exp: expSec,
    nbf: nowSec - 60,
    iat: nowSec,
    jti: `jwt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    username: claims.username || 'Valeros of Korvosa',
    preferred_username: claims.username || 'Valeros of Korvosa',
    name: claims.display_name || claims.username || 'Valeros of Korvosa',
    email: claims.email || 'valeros@runefoble.dev',
    email_verified: true,
    roles: claims.roles || ['player'],
    'urn:zitadel:iam:org:project:roles': claims.roles || ['player'],
    is_admin: Boolean(claims.is_admin || claims.roles?.includes('admin')),
    display_name: claims.display_name || claims.username || 'Valeros of Korvosa',
    bio: claims.bio || '',
  };

  const encodeBase64Url = (obj: unknown): string => {
    const json = JSON.stringify(obj);
    return Buffer.from(json)
      .toString('base64')
      .replace(/=/g, '')
      .replace(/\+/g, '-')
      .replace(/\//g, '_');
  };

  const headerB64 = encodeBase64Url(header);
  const payloadB64 = encodeBase64Url(payload);
  const mockSignature = Buffer.from('mock-zitadel-signature-for-frontdoor-bdd')
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');

  return `${headerB64}.${payloadB64}.${mockSignature}`;
}

export class AuthFixtures {
  constructor(
    private page: Page,
    private _context: BrowserContext
  ) {}

  public resolvePersona(roleOrName: string): UserClaims {
    const normalized = roleOrName.toLowerCase().replace(/[^a-z]/g, '');
    if (normalized.includes('evelyn')) {
      return PREDEFINED_PERSONAS.evelyn;
    }
    if (normalized.includes('valeros')) {
      return PREDEFINED_PERSONAS.valeros;
    }
    if (normalized.includes('sarah')) {
      return PREDEFINED_PERSONAS.sarah;
    }
    if (normalized.includes('dm') || normalized.includes('master') || normalized.includes('gm')) {
      return PREDEFINED_PERSONAS.dm;
    }
    if (normalized.includes('spectator')) {
      return PREDEFINED_PERSONAS.spectator;
    }
    return PREDEFINED_PERSONAS.player;
  }

  async injectUserIntoPage(targetPage: Page, roleOrName: string, customClaims?: Partial<UserClaims>): Promise<TestUser> {
    const baseClaims = this.resolvePersona(roleOrName);
    const finalClaims: UserClaims = { ...baseClaims, ...customClaims };
    const token = createMockJwt(finalClaims);

    const sessionPayload = {
      tokens: {
        accessToken: token,
        refreshToken: 'mock-refresh-token-frontdoor',
        expiresAt: Date.now() + 86400 * 1000 * 7,
      },
      user: finalClaims,
    };

    const sessionJson = JSON.stringify(sessionPayload);
    const userJson = JSON.stringify(finalClaims);

    // Inject into localStorage for subsequent page loads
    await targetPage.addInitScript(
      ({ sJson, tok, uJson }) => {
        try {
          window.localStorage.setItem('rf_auth_session', sJson);
          window.localStorage.setItem('runefoble-access-token', tok);
          window.localStorage.setItem('runefoble-user', uJson);
        } catch {
          // Ignore restricted localStorage in sandbox
        }
      },
      { sJson: sessionJson, tok: token, uJson: userJson }
    );

    // If page is currently navigated to an existing document, update active localStorage
    try {
      await targetPage.evaluate(
        ({ sJson, tok, uJson, detailState }) => {
          if (typeof window !== 'undefined' && window.localStorage) {
            window.localStorage.setItem('rf_auth_session', sJson);
            window.localStorage.setItem('runefoble-access-token', tok);
            window.localStorage.setItem('runefoble-user', uJson);
            window.dispatchEvent(
              new CustomEvent('rf-auth-changed', {
                detail: detailState,
                bubbles: true,
                composed: true,
              })
            );
          }
        },
        {
          sJson: sessionJson,
          tok: token,
          uJson: userJson,
          detailState: {
            isAuthenticated: true,
            user: finalClaims,
            tokens: sessionPayload.tokens,
          },
        }
      );
    } catch {
      // Ignored if called before initial page navigation
    }

    return {
      userId: finalClaims.user_id,
      username: finalClaims.username,
      roles: finalClaims.roles,
      token,
      isAdmin: finalClaims.is_admin,
    };
  }

  async injectUser(roleOrName: string, customClaims?: Partial<UserClaims>): Promise<TestUser> {
    return this.injectUserIntoPage(this.page, roleOrName, customClaims);
  }

  async clearAuth(): Promise<void> {
    await this.page.evaluate(() => {
      window.localStorage.removeItem('rf_auth_session');
      window.localStorage.removeItem('runefoble-access-token');
      window.localStorage.removeItem('runefoble-user');
      window.dispatchEvent(
        new CustomEvent('rf-auth-changed', {
          detail: { isAuthenticated: false, user: null, tokens: null },
          bubbles: true,
          composed: true,
        })
      );
    });
  }
}
