import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { ContextProvider } from '@lit/context';
import { authContext } from './auth-context.ts';

/**
 * Storybook stand-in for the App Shell auth provider. Wrap a microfrontend in it
 * to give the microfrontend a fixed token. Do not use it in the shell.
 */
@customElement('runefoble-story-auth-provider')
export class RunefobleStoryAuthProvider extends LitElement {
  @property({ type: String }) token: string | null = null;

  readonly provider = new ContextProvider(this, {
    context: authContext,
    initialValue: { getAccessToken: async () => this.token },
  });

  render() {
    return html`<slot></slot>`;
  }
}
