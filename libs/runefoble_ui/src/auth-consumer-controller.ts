import { ContextConsumer } from '@lit/context';
import type { ReactiveControllerHost } from 'lit';
import { authContext, type AuthContextValue } from './auth-context.ts';

type AuthHost = ReactiveControllerHost & HTMLElement;

/**
 * Lets a microfrontend read the shell's auth context.
 * With no provider (for example Storybook alone), no token is available.
 */
export class AuthConsumerController {
  private readonly consumer: ContextConsumer<typeof authContext, AuthHost>;

  constructor(host: AuthHost) {
    this.consumer = new ContextConsumer(host, { context: authContext, subscribe: true });
  }

  get provided(): AuthContextValue | undefined {
    return this.consumer.value;
  }

  async getAccessToken(): Promise<string | null> {
    return (await this.provided?.getAccessToken()) ?? null;
  }

  /** Returns `{ Authorization: 'Bearer ...' }` when a token exists, else an empty object. */
  async authHeaders(): Promise<Record<string, string>> {
    const token = await this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}
