/**
 * Runefoble Playwright BDD World Context Storage
 * Governed by ADR-0014 and Hard Invariant 7 (Frontdoor Blackbox TDD).
 */

export interface TestUser {
  userId: string;
  username: string;
  roles: string[];
  token?: string;
  isAdmin?: boolean;
}

export class World {
  public currentUser: TestUser | null = null;
  public campaignId: string | null = null;
  public campaignTitle: string | null = null;
  public sessionId: string | null = null;
  public characterId: string | null = null;
  public activeTheme: string | null = null;
  public customState: Map<string, unknown> = new Map();

  reset(): void {
    this.currentUser = null;
    this.campaignId = null;
    this.campaignTitle = null;
    this.sessionId = null;
    this.characterId = null;
    this.activeTheme = null;
    this.customState.clear();
  }

  set(key: string, value: unknown): void {
    this.customState.set(key, value);
  }

  get<T>(key: string): T | undefined {
    return this.customState.get(key) as T | undefined;
  }
}
