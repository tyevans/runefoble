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
