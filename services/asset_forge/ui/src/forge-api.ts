/**
 * HTTP client for the Asset Forge routes (services/asset_forge).
 * TASK-0613: Asset Forge and Print Forge Components Call Forge API and Show Results.
 * Token placement calls the board_state token route (services/board_state).
 *
 * Every call posts to a forge route and resolves only with the response body.
 * A non-2xx response rejects with ForgeApiError that carries the server detail.
 * A 401 or 403 rejects with ForgeAuthError. Network failures reject with the fetch error.
 * Nothing resolves on failure.
 *
 * TASK-0812: every call takes the shared auth source (the same one AssetImageController uses,
 * `AuthConsumerController.authHeaders`) and sends its headers, so the bearer reaches the gateway.
 */

export type FetchLike = typeof fetch;

/** Resolves the headers that carry the caller's bearer. Empty when nobody is signed in. */
export type AuthHeaders = () => Promise<Record<string, string>>;

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

/** The server refused the caller (401 or 403). The message tells the player what to do. */
export class ForgeAuthError extends ForgeApiError {
  constructor(status: 401 | 403) {
    super(
      status === 401
        ? 'Sign in to use the forge. Your session is missing or has expired.'
        : 'Your account does not have permission for this forge action.',
      status,
    );
    this.name = 'ForgeAuthError';
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
  authHeaders: AuthHeaders,
  url: string,
  body: Record<string, unknown>,
): Promise<TResponse> {
  const res = await fetchImpl(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (res.status === 401 || res.status === 403) {
    throw new ForgeAuthError(res.status);
  }
  if (!res.ok) {
    throw new ForgeApiError(await readErrorMessage(res), res.status);
  }
  return (await res.json()) as TResponse;
}

export async function forgeBattlemap(
  baseUrl: string,
  input: BattlemapInput,
  authHeaders: AuthHeaders,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedMapData> {
  const res = await postForge<BattlemapResponse>(
    fetchImpl,
    authHeaders,
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
  authHeaders: AuthHeaders,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedTokenData> {
  const res = await postForge<TokenResponse>(
    fetchImpl,
    authHeaders,
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
  authHeaders: AuthHeaders,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedPrintPdf> {
  return postForge<ForgedPrintPdf>(
    fetchImpl,
    authHeaders,
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
  authHeaders: AuthHeaders,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedStandees> {
  return postForge<ForgedStandees>(
    fetchImpl,
    authHeaders,
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
  authHeaders: AuthHeaders,
  fetchImpl: FetchLike = fetch,
): Promise<ForgedStlToken> {
  return postForge<ForgedStlToken>(
    fetchImpl,
    authHeaders,
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
export async function placeBoardToken(
  baseUrl: string,
  input: PlaceBoardTokenInput,
  authHeaders: AuthHeaders,
  fetchImpl: FetchLike = fetch,
): Promise<PlacedBoardToken> {
  const url = `${baseUrl}/api/v1/boards/${encodeURIComponent(input.sessionId)}/tokens`;
  const res = await postForge<PlacedBoardToken>(fetchImpl, authHeaders, url, {
    name: input.name,
    token_type: input.tokenType,
    x: input.x,
    y: input.y,
  });
  return {
    token_id: res.token_id,
    name: res.name,
    token_type: res.token_type,
    x: res.x,
    y: res.y,
  };
}
