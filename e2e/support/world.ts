import type { BrowserContext, Page } from '@playwright/test';

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
  public extraContexts: BrowserContext[] = [];
  public userPages: Map<string, Page> = new Map();

  setPage(name: string, page: Page): void {
    this.userPages.set(name.toLowerCase(), page);
  }

  getPage(name: string): Page | undefined {
    return this.userPages.get(name.toLowerCase());
  }

  reset(): void {
    this.currentUser = null;
    this.campaignId = null;
    this.campaignTitle = null;
    this.sessionId = null;
    this.characterId = null;
    this.activeTheme = null;
    this.customState.clear();
    this.userPages.clear();
  }

  async cleanup(): Promise<void> {
    for (const ctx of this.extraContexts) {
      await ctx.close().catch(() => {});
    }
    this.extraContexts = [];
    this.reset();
  }

  set(key: string, value: unknown): void {
    this.customState.set(key, value);
  }

  get<T>(key: string): T | undefined {
    return this.customState.get(key) as T | undefined;
  }
}

