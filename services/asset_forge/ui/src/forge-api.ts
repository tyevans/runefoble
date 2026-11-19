/**
 * HTTP client for the Asset Forge routes (services/asset_forge).
 * TASK-0613: Asset Forge and Print Forge Components Call Forge API and Show Results.
 * Token placement calls the board_state token route (services/board_state).
 *
 * Every call posts to a forge route through the shared transport `postJson` in
 * `@runefoble/ui-core` (TASK-0758). `opts.apiBase` is the gateway base and `opts.auth` is the
 * caller's bearer source (TASK-0812). A non-2xx response rejects with `HttpError`. A network
 * failure rejects with the fetch error. Nothing resolves on failure.
 */

import { HttpError, postJson, requestFailureMessage, type RequestOptions } from '@runefoble/ui-core';

export interface ForgedMapData {
  asset_id: string;
  image_url: string;
  theme: string;
  width_cells: number;
  height_cells: number;
  wall_count: number;
  hazard_count: number;
}

export interface ForgedTokenData {
  asset_id: string;
  image_url: string;
  token_name: string;
  token_type: string;
  size_px: number;
}

export interface ForgedDownload {
  asset_id: string;
  download_url: string;
}

export interface ForgedPrintPdf extends ForgedDownload {
  total_pages: number;
  page_size: string;
}

export interface ForgedStandees extends ForgedDownload {
  standee_count: number;
  pages: number;
}

export interface ForgedStlToken extends ForgedDownload {
  facet_count: number;
  is_watertight: boolean;
}

export interface BattlemapInput {
  prompt: string;
  /** Campaign that owns the forge record. Required: the forge routes answer 422 without it. */
  campaignId: string;
  widthCells: number;
  heightCells: number;
}

export interface TokenInput {
  prompt: string;
  tokenName: string;
  tokenType: string;
  /** Campaign that owns the forge record. Required: the forge routes answer 422 without it. */
  campaignId: string;
}

export interface PrintPdfInput {
  title: string;
  widthCells: number;
  heightCells: number;
  pageSize: 'letter' | 'a4';
  /** Campaign that owns the forge record. Required: the forge routes answer 422 without it. */
  campaignId: string;
}

export interface StandeeInput {
  name: string;
  type: string;
  hp: number;
  color: string;
}

export interface StandeesInput {
  sheetTitle: string;
  standees: StandeeInput[];
  pageSize: 'letter' | 'a4';
  /** Campaign that owns the forge record. Required: the forge routes answer 422 without it. */
  campaignId: string;
}

export interface StlTokenInput {
  diameterMm: number;
  conditionLabel: string;
  numSlots: number;
  /** Campaign that owns the forge record. Required: the forge routes answer 422 without it. */
  campaignId: string;
}

/** Text for a refused caller. Only 401 and 403 need their own words. The server detail covers the rest. */
const AUTH_FAILURE_TEXT: Record<number, string> = {
  401: 'Sign in to use the forge. Your session is missing or has expired.',
  403: 'Your account does not have permission for this forge action.',
};

/** The message a forge element shows for a failed call. */
export function forgeFailureMessage(err: unknown): string {
  if (err instanceof HttpError) return AUTH_FAILURE_TEXT[err.status] ?? err.detail;
  if (err instanceof Error && !(err instanceof TypeError)) return err.message;
  return requestFailureMessage(err);
}

interface BattlemapResponse {
  asset_id: string;
  image_url: string;
  theme: string;
  width_cells: number;
  height_cells: number;
  wall_segments: unknown[];
  hazard_cells: unknown[];
}

interface TokenResponse {
  asset_id: string;
  image_url: string;
  token_name: string;
  token_type: string;
  size_px: number;
}

/** The message a forge element shows when it has no campaign. The element sends no request. */
export const NO_CAMPAIGN_MESSAGE = 'Open a campaign to use the forge. The forge saves each asset to a campaign.';

export async function forgeBattlemap(input: BattlemapInput, opts: RequestOptions): Promise<ForgedMapData> {
  const res = await postJson<BattlemapResponse>(
    '/api/v1/forge/battlemap',
    {
      prompt: input.prompt,
      width_cells: input.widthCells,
      height_cells: input.heightCells,
      campaign_id: input.campaignId,
    },
    opts,
  );
  return {
    asset_id: res.asset_id,
    image_url: res.image_url,
    theme: res.theme,
    width_cells: res.width_cells,
    height_cells: res.height_cells,
    wall_count: res.wall_segments.length,
    hazard_count: res.hazard_cells.length,
  };
}

export async function forgeToken(input: TokenInput, opts: RequestOptions): Promise<ForgedTokenData> {
  const res = await postJson<TokenResponse>(
    '/api/v1/forge/token',
    {
      prompt: input.prompt,
      token_name: input.tokenName,
      token_type: input.tokenType,
      campaign_id: input.campaignId,
    },
    opts,
  );
  return {
    asset_id: res.asset_id,
    image_url: res.image_url,
    token_name: res.token_name,
    token_type: res.token_type,
    size_px: res.size_px,
  };
}

export async function exportPrintPdf(input: PrintPdfInput, opts: RequestOptions): Promise<ForgedPrintPdf> {
  return postJson<ForgedPrintPdf>(
    '/api/v1/forge/print-pdf',
    {
      title: input.title,
      width_cells: input.widthCells,
      height_cells: input.heightCells,
      page_size: input.pageSize,
      format: 'json',
      campaign_id: input.campaignId,
    },
    opts,
  );
}

export async function exportStandees(input: StandeesInput, opts: RequestOptions): Promise<ForgedStandees> {
  return postJson<ForgedStandees>(
    '/api/v1/forge/standees',
    {
      sheet_title: input.sheetTitle,
      standees: input.standees,
      page_size: input.pageSize,
      format: 'json',
      campaign_id: input.campaignId,
    },
    opts,
  );
}

export async function exportStlToken(input: StlTokenInput, opts: RequestOptions): Promise<ForgedStlToken> {
  return postJson<ForgedStlToken>(
    '/api/v1/forge/stl-token',
    {
      diameter_mm: input.diameterMm,
      condition_label: input.conditionLabel,
      num_slots: input.numSlots,
      format: 'json',
      campaign_id: input.campaignId,
    },
    opts,
  );
}

export interface PlaceBoardTokenInput {
  sessionId: string;
  name: string;
  tokenType: string;
  x: number;
  y: number;
}

export interface PlacedBoardToken {
  token_id: string;
  name: string;
  token_type: string;
  x: number;
  y: number;
}

/** Places a token on a board through the board_state route. Requires a session id. */
export async function placeBoardToken(input: PlaceBoardTokenInput, opts: RequestOptions): Promise<PlacedBoardToken> {
  const path = `/api/v1/boards/${encodeURIComponent(input.sessionId)}/tokens`;
  const res = await postJson<PlacedBoardToken>(path, {
    name: input.name,
    token_type: input.tokenType,
    x: input.x,
    y: input.y,
  }, opts);
  return {
    token_id: res.token_id,
    name: res.name,
    token_type: res.token_type,
    x: res.x,
    y: res.y,
  };
}
