/**
 * Storybook helper. Replaces `window.fetch` with a server stand-in that answers 200 with `body`
 * when the request carries `Authorization: Bearer <token>`, and 401 otherwise.
 * It makes stories show the auth contract without a live gateway or console network errors.
 */
export function installTokenCheckingFetch(token: string, body: unknown): void {
  window.fetch = async (_input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers);
    if (headers.get('Authorization') === `Bearer ${token}`) {
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    return new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 });
  };
}

export interface AssetUploadStoryRoutes {
  /** Substring of the upload URL, for example "/api/v1/assets/upload". */
  uploadPath: string;
  /** Upload response body. Its `download_url` is the protected read path. */
  uploadBody: Record<string, unknown>;
  /** Substring of the protected read URL, for example "/api/v1/assets/asset-1". */
  readPath: string;
  /** Raw bytes returned for a read with the right bearer. */
  assetBody: string;
  contentType: string;
}

/**
 * Storybook helper for protected asset flows (TASK-0784). Uploads answer with `uploadBody`.
 * Reads answer with the raw bytes only when the request carries the bearer. Any other
 * request fails, so a story never shows an image that no route produced.
 */
export function installAssetUploadFetch(token: string, routes: AssetUploadStoryRoutes): void {
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    const headers = new Headers(init?.headers);
    if (headers.get('Authorization') !== `Bearer ${token}`) {
      return new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 });
    }
    if (method === 'POST' && url.includes(routes.uploadPath)) {
      return new Response(JSON.stringify(routes.uploadBody), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (method === 'GET' && url.includes(routes.readPath)) {
      return new Response(routes.assetBody, { status: 200, headers: { 'Content-Type': routes.contentType } });
    }
    throw new Error(`Unmocked request: ${method} ${url}`);
  };
}
