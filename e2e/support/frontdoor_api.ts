/**
 * Runefoble Public Frontdoor REST API Client
 * Executes preconditions strictly through public HTTP routes per Hard Invariant 7 (No backdoors).
 * Governed by ADR-0014, ADR-0001, ADR-0010.
 */

import type { APIRequestContext } from '@playwright/test';

export interface CampaignSummary {
  id: string;
  title: string;
  description: string;
  setting: string;
  system: string;
  status: string;
  owner_id: string;
  role?: string;
}

export interface CreateCampaignOptions {
  description?: string;
  setting?: string;
  system?: string;
  token?: string;
}

export class FrontdoorApi {
  private baseUrl: string;

  constructor(
    private request: APIRequestContext,
    baseUrl = 'http://localhost:8000'
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private authHeaders(token?: string): Record<string, string> {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async checkHealth(): Promise<{ status: string }> {
    const res = await this.request.get(`${this.baseUrl}/healthz`);
    if (!res.ok()) {
      throw new Error(`Health check failed: ${res.status()} ${res.statusText()}`);
    }
    return res.json();
  }

  async listCampaigns(token?: string): Promise<CampaignSummary[]> {
    const res = await this.request.get(`${this.baseUrl}/api/v1/campaigns`, {
      headers: this.authHeaders(token),
    });
    if (!res.ok()) {
      throw new Error(`Failed to list campaigns: ${res.status()} ${res.statusText()}`);
    }
    return res.json();
  }

  async createCampaign(
    title: string,
    options: CreateCampaignOptions = {}
  ): Promise<CampaignSummary> {
    const res = await this.request.post(`${this.baseUrl}/api/v1/campaigns`, {
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(options.token),
      },
      data: {
        title,
        description: options.description || `Frontdoor test campaign: ${title}`,
        setting: options.setting || 'Forgotten Realms',
        system: options.system || '5e',
        seed_initial_session: true,
      },
    });

    if (!res.ok()) {
      const errText = await res.text();
      throw new Error(
        `Failed to create campaign "${title}": ${res.status()} ${res.statusText()} - ${errText}`
      );
    }
    return res.json();
  }

  async getCampaign(campaignId: string, token?: string): Promise<CampaignSummary> {
    const res = await this.request.get(`${this.baseUrl}/api/v1/campaigns/${campaignId}`, {
      headers: this.authHeaders(token),
    });
    if (!res.ok()) {
      throw new Error(
        `Failed to get campaign "${campaignId}": ${res.status()} ${res.statusText()}`
      );
    }
    return res.json();
  }

  async listCharacters(token?: string): Promise<any[]> {
    const res = await this.request.get(`${this.baseUrl}/api/v1/characters`, {
      headers: this.authHeaders(token),
    });
    if (!res.ok()) {
      throw new Error(`Failed to list characters: ${res.status()} ${res.statusText()}`);
    }
    return res.json();
  }

  async createCharacter(payload: Record<string, unknown>, token?: string): Promise<any> {
    const res = await this.request.post(`${this.baseUrl}/api/v1/characters`, {
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(token),
      },
      data: payload,
    });
    if (!res.ok()) {
      const errText = await res.text();
      throw new Error(`Failed to create character: ${res.status()} ${res.statusText()} - ${errText}`);
    }
    return res.json();
  }

  async getCharacter(characterId: string, token?: string): Promise<any> {
    const res = await this.request.get(`${this.baseUrl}/api/v1/characters/${characterId}`, {
      headers: this.authHeaders(token),
    });
    if (!res.ok()) {
      throw new Error(`Failed to get character "${characterId}": ${res.status()} ${res.statusText()}`);
    }
    return res.json();
  }
}

