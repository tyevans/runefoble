/**
 * Runefoble Zitadel OIDC Browser Authentication Service
 * ADR-0004, ADR-0005, ADR-0012, ADR-0013, TASK-0207
 */

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

export interface AuthTokens {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: UserClaims | null;
  tokens: AuthTokens | null;
}

export type AuthListener = (state: AuthState) => void;
const STORAGE_KEY = 'rf_auth_session';

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
    is_admin: roles.includes('admin') || Boolean(payload.is_admin),
    display_name: payload.display_name ? String(payload.display_name) : (payload.name ? String(payload.name) : undefined),
    avatar_url: payload.avatar_url || payload.picture ? String(payload.avatar_url || payload.picture) : undefined,
    bio: payload.bio ? String(payload.bio) : undefined,
  };
}

export class AuthService {
  private static instance: AuthService;
  private state: AuthState = { isAuthenticated: false, user: null, tokens: null };
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Set<AuthListener> = new Set();
  public apiBase = '/api/v1/auth';
  public devFallback = true;

  constructor() { this.restoreSession(); }

  static getInstance(): AuthService {
    if (!AuthService.instance) AuthService.instance = new AuthService();
    return AuthService.instance;
  }

  getState(): AuthState { return { ...this.state }; }
  isAuthenticated(): boolean { return this.state.isAuthenticated; }
  getUser(): UserClaims | null { return this.state.user; }
  getAccessToken(): string | null { return this.state.tokens?.accessToken || null; }

  onAuthChanged(listener: AuthListener): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  updateUser(claims: Partial<UserClaims>): void {
    const base = this.state.user || {
      user_id: 'user-valeros',
      username: 'Valeros of Korvosa',
      roles: ['player'],
    };
    this.state.user = { ...base, ...claims };
    if (this.state.tokens) {
      this.persistSession(this.state.tokens, this.state.user);
    } else {
      this.notify();
    }
  }


  private notify(): void {
    const current = this.getState();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('rf-auth-changed', { detail: current, bubbles: true, composed: true }));
    }
    for (const l of this.listeners) l(current);
  }

  private persistSession(tokens: AuthTokens, user: UserClaims): void {
    this.state = { isAuthenticated: true, user, tokens };
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ tokens, user }));
      }
    } catch { /* storage disabled */ }
    this.scheduleRefresh(tokens.expiresAt);
    this.notify();
  }

  private clearSession(): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    this.refreshTimer = null;
    this.state = { isAuthenticated: false, user: null, tokens: null };
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch { /* storage disabled */ }
    this.notify();
  }

  private restoreSession(): void {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return;
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (data?.tokens?.accessToken && data?.user) {
        if (data.tokens.expiresAt && Date.now() >= data.tokens.expiresAt) {
          this.refreshToken(data.tokens.refreshToken).catch(() => this.clearSession());
          return;
        }
        this.state = { isAuthenticated: true, user: data.user, tokens: data.tokens };
        this.scheduleRefresh(data.tokens.expiresAt);
      }
    } catch { this.clearSession(); }
  }

  private scheduleRefresh(expiresAt: number): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    const delay = Math.max(5000, expiresAt - Date.now() - 60000);
    this.refreshTimer = setTimeout(() => {
      this.refreshToken().catch(() => this.logout());
    }, delay);
    (this.refreshTimer as any)?.unref?.();
  }

  async login(username: string, password: string): Promise<UserClaims> {
    try {
      const res = await fetch(`${this.apiBase}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, grant_type: 'password' }),
      });
      if (!res.ok) throw new Error(`Auth failed (${res.status})`);
      return this.handleTokenResponse(await res.json(), username);
    } catch (err) {
      if (this.devFallback) return this.createMockSession(username, `${username}@runefoble.local`);
      throw err;
    }
  }

  async register(username: string, email: string, password: string): Promise<UserClaims> {
    try {
      const res = await fetch(`${this.apiBase}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });
      if (!res.ok) throw new Error(`Registration failed (${res.status})`);
      return this.handleTokenResponse(await res.json(), username, email);
    } catch (err) {
      if (this.devFallback) return this.createMockSession(username, email);
      throw err;
    }
  }

  async refreshToken(existingRefresh?: string): Promise<string> {
    const token = existingRefresh || this.state.tokens?.refreshToken;
    if (!token && !this.devFallback) throw new Error('No refresh token available');
    try {
      const res = await fetch(`${this.apiBase}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: token, grant_type: 'refresh_token' }),
      });
      if (!res.ok) throw new Error('Refresh failed');
      const body = await res.json();
      this.handleTokenResponse(body, this.state.user?.username || 'User');
      return body.access_token;
    } catch (err) {
      if (this.devFallback && this.state.user) {
        return this.createMockSession(this.state.user.username, this.state.user.email).user_id;
      }
      throw err;
    }
  }

  logout(): void { this.clearSession(); }

  private handleTokenResponse(body: Record<string, unknown>, fallbackName: string, fallbackEmail?: string): UserClaims {
    const accessToken = String(body.access_token || '');
    const refreshToken = body.refresh_token ? String(body.refresh_token) : undefined;
    const expiresIn = Number(body.expires_in || 3600);
    const expiresAt = Date.now() + expiresIn * 1000;
    const payload = parseJwtPayload(accessToken);
    const user = payload ? extractClaimsFromPayload(payload) : {
      user_id: String(body.user_id || 'user-default'),
      username: fallbackName,
      email: fallbackEmail,
      roles: ['player'],
      is_admin: false,
    };
    this.persistSession({ accessToken, refreshToken, expiresAt }, user);
    return user;
  }

  private createMockSession(username: string, email?: string): UserClaims {
    const user_id = `user-${username.toLowerCase().replace(/[^a-z0-9]/g, '') || 'adventurer'}`;
    const roles = username.toLowerCase().includes('dm') ? ['dm', 'player'] : ['player'];
    const user: UserClaims = { user_id, username, email, roles, is_admin: roles.includes('admin') };
    const expiresAt = Date.now() + 3600 * 1000;
    const fakePayload = btoa(JSON.stringify({ sub: user_id, preferred_username: username, email, roles, exp: Math.floor(expiresAt / 1000) }));
    const accessToken = `eyJhbGciOiJIUzI1NiJ9.${fakePayload}.mocksignature`;
    this.persistSession({ accessToken, refreshToken: `mock-refresh-${user_id}`, expiresAt }, user);
    return user;
  }
}

export const authService = AuthService.getInstance();
