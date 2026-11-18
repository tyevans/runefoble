/**
 * Campaign Hub Data Client (TASK-0646).
 *
 * Reads the atlas, codex, and analytics views through the gateway. Every call returns a
 * DataResult. A response with an unexpected shape is a failure, never a substitute value.
 */

import type { AtlasPin, AtlasTerritory, LoreEntry } from '@runefoble/campaign-lore-ui';
import type { CampaignHeatmapResponse, CampaignMvpResponse, CampaignTimelineResponse } from '@runefoble/campaign-analytics-ui';
import { dataFailure, dataOk, UNREADABLE_RESPONSE_MESSAGE, type DataResult } from './data-result.ts';

export interface CampaignAtlasView { pins: AtlasPin[]; territories: AtlasTerritory[] }
export interface CampaignAnalyticsView { heatmap: CampaignHeatmapResponse; mvp: CampaignMvpResponse; timeline: CampaignTimelineResponse }

/** The request method of AppDataService. The caller binds it, so the generic is kept. */
export type GatewayRequest = <T>(path: string) => Promise<DataResult<T>>;

/** The write method of AppDataService. The caller binds it, so the generic is kept. */
export type GatewayWrite = <T>(path: string, init: RequestInit) => Promise<DataResult<T>>;

export interface CodexEntryPayload { title: string; content: string; privacy: string }

export interface AtlasPinPayload { title: string; coordinates: { x: number; y: number }; layer: string }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function entityName(entity: unknown): string {
  if (typeof entity === 'string') return entity;
  if (isRecord(entity) && typeof entity.name === 'string') return entity.name;
  return '';
}

/** Maps a lore codex entry (gateway shape) to the codex element shape. */
export function toLoreEntry(raw: Record<string, unknown>): LoreEntry {
  const linked = Array.isArray(raw.linked_entities) ? raw.linked_entities : [];
  return {
    id: String(raw.entry_id ?? ''),
    title: String(raw.title ?? ''),
    text: String(raw.content ?? ''),
    entities: linked.map(entityName).filter((name) => name !== ''),
    isSecret: raw.privacy === 'private',
  };
}

export async function fetchCampaignAtlasView(request: GatewayRequest, campaignId: string): Promise<DataResult<CampaignAtlasView>> {
  const res = await request<Partial<CampaignAtlasView>>(`/campaigns/${encodeURIComponent(campaignId)}/atlas`);
  if (!res.ok) return res;
  if (!isRecord(res.data) || !Array.isArray(res.data.pins) || !Array.isArray(res.data.territories)) {
    return dataFailure(0, UNREADABLE_RESPONSE_MESSAGE);
  }
  return dataOk({ pins: res.data.pins, territories: res.data.territories });
}

export async function fetchCampaignLoreEntries(request: GatewayRequest, campaignId: string): Promise<DataResult<LoreEntry[]>> {
  const res = await request<unknown>(`/campaigns/${encodeURIComponent(campaignId)}/codex`);
  if (!res.ok) return res;
  if (!Array.isArray(res.data) || !res.data.every(isRecord)) return dataFailure(0, UNREADABLE_RESPONSE_MESSAGE);
  return dataOk(res.data.map(toLoreEntry));
}

/** Places a milestone pin through the gateway. A refused or unreachable write returns a failure. */
export async function createAtlasPin(write: GatewayWrite, campaignId: string, payload: AtlasPinPayload): Promise<DataResult<AtlasPin>> {
  const res = await write<AtlasPin>(`/campaigns/${encodeURIComponent(campaignId)}/atlas/pins`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) return res;
  if (!isRecord(res.data) || typeof res.data.pin_id !== 'string') return dataFailure(0, UNREADABLE_RESPONSE_MESSAGE);
  return dataOk(res.data);
}

/** Publishes a codex entry through the gateway. A refused or unreachable write returns a failure. */
export async function createCodexEntry(write: GatewayWrite, campaignId: string, payload: CodexEntryPayload): Promise<DataResult<Record<string, unknown>>> {
  const res = await write<Record<string, unknown>>(`/campaigns/${encodeURIComponent(campaignId)}/codex/entries`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) return res;
  if (!isRecord(res.data) || typeof res.data.entry_id !== 'string') return dataFailure(0, UNREADABLE_RESPONSE_MESSAGE);
  return dataOk(res.data);
}

export async function fetchCampaignAnalyticsView(request: GatewayRequest, campaignId: string): Promise<DataResult<CampaignAnalyticsView>> {
  const id = encodeURIComponent(campaignId);
  const [heatmap, mvp, timeline] = await Promise.all([
    request<CampaignHeatmapResponse>(`/analytics/campaigns/${id}/heatmap`),
    request<CampaignMvpResponse>(`/analytics/campaigns/${id}/mvp`),
    request<CampaignTimelineResponse>(`/analytics/campaigns/${id}/timeline`),
  ]);
  if (!heatmap.ok) return heatmap;
  if (!mvp.ok) return mvp;
  if (!timeline.ok) return timeline;
  return dataOk({ heatmap: heatmap.data, mvp: mvp.data, timeline: timeline.data });
}
