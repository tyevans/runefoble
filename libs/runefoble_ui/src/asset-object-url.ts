/**
 * Browser reads of protected media (TASK-0784).
 *
 * `<img src>` cannot send an `Authorization` header. Asset reads need a bearer and
 * `forged_asset.view`, so a microfrontend fetches the bytes with the shared bearer and
 * shows them through a blob URL. The blob URL lives only in this document. Do not store it.
 */

export type AssetFetchLike = (input: string, init?: RequestInit) => Promise<Response>;

/**
 * Fetches a protected asset with the caller's bearer and returns a blob URL for `<img src>`.
 * Rejects when the server refuses the request. It never returns a substitute URL.
 */
export async function fetchAssetObjectUrl(
  url: string,
  authHeaders: () => Promise<Record<string, string>>,
  fetchImpl: AssetFetchLike = (input, init) => fetch(input, init),
): Promise<string> {
  const response = await fetchImpl(url, { headers: await authHeaders() });
  if (!response.ok) {
    throw new Error(`Asset request for ${url} failed with status ${response.status}.`);
  }
  return URL.createObjectURL(await response.blob());
}

/** Releases a blob URL made by `fetchAssetObjectUrl`. Other URLs pass through untouched. */
export function revokeAssetObjectUrl(url: string | null | undefined): void {
  if (url?.startsWith('blob:')) URL.revokeObjectURL(url);
}
