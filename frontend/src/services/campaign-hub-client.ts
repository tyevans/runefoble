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
