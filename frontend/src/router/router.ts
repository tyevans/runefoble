/**
 * Runefoble Lightweight SPA Client Router
 * ADR-0004, ADR-0012, ADR-0013, TASK-0206, TASK-0247
 */

export interface RouteParams { [key: string]: string; }
export interface BreadcrumbItem { label: string; path?: string; active?: boolean; }
export interface MatchedRoute {
  path: string;
  pattern: string;
  params: RouteParams;
  query: Record<string, string>;
  breadcrumbs: BreadcrumbItem[];
}

export type RouteGuard = (to: MatchedRoute, from: MatchedRoute | null) => boolean | string | Promise<boolean | string>;
export type RouteListener = (route: MatchedRoute, prev: MatchedRoute | null) => void;
export type TeardownHandler = () => void | Promise<void>;
export type TitleResolver = (type: string, id: string) => string | undefined;
export type AsyncTitleResolver = (type: string, id: string) => Promise<string | undefined>;

interface RouteDefinition {
  pattern: string;
  paramNames: string[];
  regex: RegExp;
}

export const STANDARD_ROUTES = [
  '#/login', '#/register', '#/campaigns', '#/campaigns/:campaignId',
  '#/campaigns/:campaignId/characters', '#/campaigns/:campaignId/lobby/:sessionId',
  '#/campaigns/:campaignId/sessions/:sessionId', '#/characters', '#/characters/:characterId', '#/profile',
] as const;

export class Router {
  private static instance: Router;
  private routes: RouteDefinition[] = [];
  private guards: RouteGuard[] = [];
  private listeners: Set<RouteListener> = new Set();
  private teardownHandlers: Set<TeardownHandler> = new Set();
  private titleResolvers: TitleResolver[] = [];
  private asyncTitleResolvers: AsyncTitleResolver[] = [];
  private routeTitles: Map<string, string> = new Map();
  private current: MatchedRoute | null = null;
  private previous: MatchedRoute | null = null;
  private boundHashChange: (() => void) | null = null;

  constructor() {
    for (const pattern of STANDARD_ROUTES) this.addRoute(pattern);
  }

  static getInstance(): Router {
    if (!Router.instance) Router.instance = new Router();
    return Router.instance;
  }

  addRoute(pattern: string): void {
    const cleanPattern = pattern.replace(/^#?\/?/, '');
    const paramNames: string[] = [];
    const segments = cleanPattern.split('/');
    const regexParts = segments.map((seg) => {
      if (seg.startsWith(':')) { paramNames.push(seg.slice(1)); return '([^/?]+)'; }
      return seg.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    });
    this.routes.push({ pattern, paramNames, regex: new RegExp(`^#?\\/?${regexParts.join('\\/')}(?:\\?(.*))?$`) });
  }

  beforeEach(guard: RouteGuard): () => void {
    this.guards.push(guard);
    return () => { this.guards = this.guards.filter((g) => g !== guard); };
  }

  onRouteChanged(listener: RouteListener): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  registerTeardown(handler: TeardownHandler): () => void {
    this.teardownHandlers.add(handler);
    return () => { this.teardownHandlers.delete(handler); };
  }

  setTitleResolver(resolver: TitleResolver): void { this.titleResolvers.push(resolver); }
  setAsyncTitleResolver(resolver: AsyncTitleResolver): void { this.asyncTitleResolvers.push(resolver); }
  setRouteTitle(key: string, title: string): void { this.routeTitles.set(key, title); }

  resolveTitle(type: string, id: string): string | undefined {
    const direct = this.routeTitles.get(`${type}:${id}`) || this.routeTitles.get(id);
    if (direct) return direct;
    for (const res of this.titleResolvers) {
      const val = res(type, id);
      if (val) return val;
    }
    return undefined;
  }

  async resolveTitleAsync(type: string, id: string): Promise<string | undefined> {
    const syncVal = this.resolveTitle(type, id);
    if (syncVal) return syncVal;
    for (const res of this.asyncTitleResolvers) {
      try {
        const val = await res(type, id);
        if (val) {
          this.routeTitles.set(`${type}:${id}`, val);
          return val;
        }
      } catch (err) {
        console.error(`Error resolving title for ${type}:${id}:`, err);
      }
    }
    return undefined;
  }

  private async resolveRouteTitles(route: MatchedRoute): Promise<void> {
    for (const [key, value] of Object.entries(route.params)) {
      if (key.endsWith('Id')) await this.resolveTitleAsync(key.slice(0, -2), value);
    }
    if (route.params.sessionId && route.pattern.includes('/lobby/')) {
      await this.resolveTitleAsync('lobby', route.params.sessionId);
    }
  }

  match(rawPath: string): MatchedRoute | null {
    const normalized = rawPath.trim() || '#/campaigns';
    const cleanPath = (normalized.startsWith('#') ? normalized : `#${normalized}`).split('?')[0];
    const queryString = normalized.includes('?') ? normalized.split('?')[1] : '';
    const query: Record<string, string> = {};
    if (queryString) for (const [k, v] of new URLSearchParams(queryString)) query[k] = v;
    for (const route of this.routes) {
      const match = cleanPath.match(route.regex);
      if (match) {
        const params: RouteParams = {};
        route.paramNames.forEach((name, idx) => { params[name] = match[idx + 1]; });
        return { path: cleanPath, pattern: route.pattern, params, query, breadcrumbs: this.generateBreadcrumbs(cleanPath, route.pattern, params) };
      }
    }
    const segments = cleanPath.replace(/^#?\/?/, '').split('/').filter(Boolean);
    return segments.length > 0 ? { path: cleanPath, pattern: cleanPath, params: {}, query, breadcrumbs: this.generateBreadcrumbs(cleanPath, cleanPath, {}) } : null;
  }

  private generateBreadcrumbs(path: string, pattern: string, params: RouteParams): BreadcrumbItem[] {
    const cTitle = () => this.resolveTitle('campaign', params.campaignId) || `Campaign #${params.campaignId}`;
    if (pattern === '#/campaigns') return [{ label: 'Campaigns', path: '#/campaigns', active: true }];
    if (pattern === '#/campaigns/:campaignId') return [{ label: 'Campaigns', path: '#/campaigns' }, { label: cTitle(), path, active: true }];
    if (pattern === '#/campaigns/:campaignId/characters') return [{ label: 'Campaigns', path: '#/campaigns' }, { label: cTitle(), path: `#/campaigns/${params.campaignId}` }, { label: 'Party', path, active: true }];
    if (pattern === '#/campaigns/:campaignId/lobby/:sessionId') {
      const lTitle = this.resolveTitle('lobby', params.sessionId) || this.resolveTitle('session', params.sessionId) || `Lobby ${params.sessionId}`;
      return [{ label: 'Campaigns', path: '#/campaigns' }, { label: cTitle(), path: `#/campaigns/${params.campaignId}` }, { label: lTitle, path, active: true }];
    }
    if (pattern === '#/campaigns/:campaignId/sessions/:sessionId') {
      const sTitle = this.resolveTitle('session', params.sessionId) || `Session #${params.sessionId}`;
      return [{ label: 'Campaigns', path: '#/campaigns' }, { label: cTitle(), path: `#/campaigns/${params.campaignId}` }, { label: sTitle, path, active: true }];
    }
    if (pattern === '#/characters') return [{ label: 'Characters', path: '#/characters', active: true }];
    if (pattern === '#/characters/:characterId') {
      const charTitle = this.resolveTitle('character', params.characterId) || 'Character Sheet';
      return [
        { label: 'Home', path: '#/campaigns' },
        { label: 'Characters', path: '#/characters' },
        { label: charTitle, path, active: true },
      ];
    }
    if (pattern === '#/profile') return [{ label: 'Profile', path: '#/profile', active: true }];
    if (pattern === '#/login') return [{ label: 'Login', path: '#/login', active: true }];
    if (pattern === '#/register') return [{ label: 'Register', path: '#/register', active: true }];
    const segments = path.replace(/^#?\/?/, '').split('/');
    return segments.map((seg, idx) => ({ label: seg.charAt(0).toUpperCase() + seg.slice(1), path: `#/${segments.slice(0, idx + 1).join('/')}`, active: idx === segments.length - 1 }));
  }

  async navigate(path: string, options?: { replace?: boolean }): Promise<boolean> {
    const target = this.match(path) || this.match('#/campaigns');
    if (!target) return false;
    for (const guard of this.guards) {
      const allowed = await guard(target, this.current);
      if (allowed === false) return false;
      if (typeof allowed === 'string') return this.navigate(allowed, options);
    }
    await this.resolveRouteTitles(target);
    target.breadcrumbs = this.generateBreadcrumbs(target.path, target.pattern, target.params);
    await this.teardownCurrentRoute();
    this.previous = this.current;
    this.current = target;
    if (typeof window !== 'undefined' && window.location) {
      if (window.location.hash !== target.path) {
        if (options?.replace) window.location.replace(target.path);
        else window.location.hash = target.path;
      }
      window.dispatchEvent(new CustomEvent('route-changed', { detail: { route: target, previousRoute: this.previous }, bubbles: true, composed: true }));
    }
    for (const listener of this.listeners) listener(target, this.previous);
    return true;
  }

  async teardownCurrentRoute(): Promise<void> {
    for (const handler of Array.from(this.teardownHandlers)) {
      try { await handler(); } catch (err) { console.error('Route teardown error:', err); }
    }
    this.teardownHandlers.clear();
  }

  getCurrentRoute(): MatchedRoute | null { return this.current; }
  getPreviousRoute(): MatchedRoute | null { return this.previous; }

  start(): void {
    if (typeof window === 'undefined') return;
    this.boundHashChange = () => {
      const hash = window.location.hash || '#/campaigns';
      if (!this.current || this.current.path !== hash) this.navigate(hash);
    };
    window.addEventListener('hashchange', this.boundHashChange);
    this.navigate(window.location.hash || '#/campaigns');
  }

  stop(): void {
    if (typeof window !== 'undefined' && this.boundHashChange) {
      window.removeEventListener('hashchange', this.boundHashChange);
      this.boundHashChange = null;
    }
    this.teardownCurrentRoute();
  }

  reset(): void {
    this.stop();
    this.guards = [];
    this.listeners.clear();
    this.teardownHandlers.clear();
    this.titleResolvers = [];
    this.asyncTitleResolvers = [];
    this.routeTitles.clear();
    this.current = null;
    this.previous = null;
  }
}

export const router = Router.getInstance();
