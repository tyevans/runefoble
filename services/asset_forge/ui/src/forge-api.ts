/**
 * HTTP client for the Asset Forge routes (services/asset_forge).
 * TASK-0613: Asset Forge and Print Forge Components Call Forge API and Show Results.
 *
 * Every call posts to a forge route and resolves only with the response body.
 * A non-2xx response rejects with ForgeApiError that carries the server detail.
 * Network failures reject with the fetch error. Nothing resolves on failure.
 */

export type FetchLike = typeof fetch;

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
  campaignId?: string;
  widthCells: number;
  heightCells: number;
}

export interface TokenInput {
  prompt: string;
  tokenName: string;
  tokenType: string;
  campaignId?: string;
}

export interface PrintPdfInput {
  title: string;
  widthCells: number;
  heightCells: number;
  pageSize: 'letter' | 'a4';
  campaignId?: string;
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
  campaignId?: string;
}

export interface StlTokenInput {
  diameterMm: number;
  conditionLabel: string;
  numSlots: number;
  campaignId?: string;
}

export class ForgeApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ForgeApiError';
    this.status = status;
  }
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function withCampaign(body: Record<string, unknown>, campaignId: string | undefined) {
  return campaignId ? { ...body, campaign_id: campaignId } : body;
}

async function readErrorMessage(res: Response): Promise<string> {
  const fallback = `Forge request failed with HTTP ${res.status}.`;
  let payload: unknown;
  try {
    payload = await res.json();
  } catch {
    return fallback;
  }
  const detail = isRecord(payload) ? payload.detail : undefined;
  if (typeof detail === 'string' && detail.length > 0) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (isRecord(item) && typeof item.msg === 'string' ? item.msg : ''))
      .filter((msg) => msg.length > 0);
    if (messages.length > 0) {
      return messages.join('; ');
    }
  }
  return fallback;
}

async function postForge<TResponse>(
  fetchImpl: FetchLike,
  url: string,
  body: Record<string, unknown>,
): Promise<TResponse> {
  const res = await fetchImpl(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ForgeApiError(await readErrorMessage(res), res.status);
  }
  return (await res.json()) as TResponse;
}

export async function forgeBattlemap(
  baseUrl: string,
  input: BattlemapInput,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedMapData> {
  const res = await postForge<BattlemapResponse>(
    fetchImpl,
    `${baseUrl}/api/v1/forge/battlemap`,
    withCampaign(
      {
        prompt: input.prompt,
        width_cells: input.widthCells,
        height_cells: input.heightCells,
      },
      input.campaignId,
    ),
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

export async function forgeToken(
  baseUrl: string,
  input: TokenInput,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedTokenData> {
  const res = await postForge<TokenResponse>(
    fetchImpl,
    `${baseUrl}/api/v1/forge/token`,
    withCampaign(
      {
        prompt: input.prompt,
        token_name: input.tokenName,
        token_type: input.tokenType,
      },
      input.campaignId,
    ),
  );
  return {
    asset_id: res.asset_id,
    image_url: res.image_url,
    token_name: res.token_name,
    token_type: res.token_type,
    size_px: res.size_px,
  };
}

export async function exportPrintPdf(
  baseUrl: string,
  input: PrintPdfInput,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedPrintPdf> {
  return postForge<ForgedPrintPdf>(
    fetchImpl,
    `${baseUrl}/api/v1/forge/print-pdf`,
    withCampaign(
      {
        title: input.title,
        width_cells: input.widthCells,
        height_cells: input.heightCells,
        page_size: input.pageSize,
        format: 'json',
      },
      input.campaignId,
    ),
  );
}

export async function exportStandees(
  baseUrl: string,
  input: StandeesInput,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedStandees> {
  return postForge<ForgedStandees>(
    fetchImpl,
    `${baseUrl}/api/v1/forge/standees`,
    withCampaign(
      {
        sheet_title: input.sheetTitle,
        standees: input.standees,
        page_size: input.pageSize,
        format: 'json',
      },
      input.campaignId,
    ),
  );
}

export async function exportStlToken(
  baseUrl: string,
  input: StlTokenInput,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedStlToken> {
  return postForge<ForgedStlToken>(
    fetchImpl,
    `${baseUrl}/api/v1/forge/stl-token`,
    withCampaign(
      {
        diameter_mm: input.diameterMm,
        condition_label: input.conditionLabel,
        num_slots: input.numSlots,
        format: 'json',
      },
      input.campaignId,
    ),
  );
}
