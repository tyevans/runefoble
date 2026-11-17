/**
 * Storybook helper: replaces the global fetch with canned forge responses.
 * TASK-0613: stories exercise the forge request path without a running service.
 *
 * Each request must match one route. An unmatched request throws, so a story
 * never shows a result that no route produced. The replacement stays installed
 * until a later story installs its own routes.
 */

export interface MockRoute {
  /** Substring of the request URL, for example "/api/v1/forge/battlemap". */
  match: string;
  status: number;
  body: unknown;
}

export function withMockFetch(...routes: MockRoute[]) {
  return <T>(story: () => T): T => {
    globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      const route = routes.find((candidate) => url.includes(candidate.match));
      if (!route) {
        throw new Error(`Unmocked request: ${init?.method ?? 'GET'} ${url}`);
      }
      return new Response(JSON.stringify(route.body), {
        status: route.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch;
    return story();
  };
}
