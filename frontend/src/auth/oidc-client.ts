/**
 * Minimal OIDC client for a public browser app (no client secret).
 * Endpoints come from discovery (/.well-known/openid-configuration) of the configured issuer.
 * TASK-0524, PRD-0023 section 1.
 */

import type { RuntimeConfig } from './runtime-config.ts';

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface DiscoveryDocument {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  end_session_endpoint?: string;
}

export interface OidcTokenResponse {
  access_token: string;
  id_token?: string;
  refresh_token?: string;
  expires_in?: number;
}

export interface AuthorizeRequest {
  state: string;
  nonce: string;
  codeChallenge: string;
  redirectUri: string;
  signUp: boolean;
}

export interface CodeExchangeRequest {
  code: string;
  codeVerifier: string;
  redirectUri: string;
}

export class OidcClient {
  private discovery: Promise<DiscoveryDocument> | null = null;

  private readonly loadConfig: () => Promise<RuntimeConfig>;
  private readonly http: FetchLike;

  constructor(loadConfig: () => Promise<RuntimeConfig>, http: FetchLike) {
    this.loadConfig = loadConfig;
    this.http = http;
  }

  /** Builds the authorization request URL. `signUp` asks Zitadel to open its hosted registration page. */
  async buildAuthorizeUrl(request: AuthorizeRequest): Promise<string> {
    const config = await this.loadConfig();
    const doc = await this.getDiscovery();
    const url = new URL(doc.authorization_endpoint);
    url.searchParams.set('client_id', config.clientId);
    url.searchParams.set('redirect_uri', request.redirectUri);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', config.scopes.join(' '));
    url.searchParams.set('state', request.state);
    url.searchParams.set('nonce', request.nonce);
    url.searchParams.set('code_challenge', request.codeChallenge);
    url.searchParams.set('code_challenge_method', 'S256');
    if (request.signUp) url.searchParams.set('prompt', 'create');
    return url.toString();
  }

  async exchangeCode(request: CodeExchangeRequest): Promise<OidcTokenResponse> {
    const config = await this.loadConfig();
    return this.postToken({
      grant_type: 'authorization_code',
      code: request.code,
      code_verifier: request.codeVerifier,
      redirect_uri: request.redirectUri,
      client_id: config.clientId,
    });
  }

  async refresh(refreshToken: string): Promise<OidcTokenResponse> {
    const config = await this.loadConfig();
    return this.postToken({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: config.clientId,
    });
  }

  /** Builds the Zitadel end-session URL. Throws when discovery does not publish one. */
  async endSessionUrl(idTokenHint: string, postLogoutRedirectUri: string): Promise<string> {
    const config = await this.loadConfig();
    const doc = await this.getDiscovery();
    if (!doc.end_session_endpoint) throw new Error('Identity provider does not publish an end-session endpoint.');
    const url = new URL(doc.end_session_endpoint);
    url.searchParams.set('id_token_hint', idTokenHint);
    url.searchParams.set('post_logout_redirect_uri', postLogoutRedirectUri);
    url.searchParams.set('client_id', config.clientId);
    return url.toString();
  }

  private getDiscovery(): Promise<DiscoveryDocument> {
    if (!this.discovery) {
      this.discovery = this.fetchDiscovery().catch((err) => {
        this.discovery = null;
        throw err;
      });
    }
    return this.discovery;
  }

  private async fetchDiscovery(): Promise<DiscoveryDocument> {
    const config = await this.loadConfig();
    const res = await this.http(`${config.issuer}/.well-known/openid-configuration`);
    if (!res.ok) throw new Error(`Discovery failed (${res.status}).`);
    const doc = (await res.json()) as Partial<DiscoveryDocument>;
    if (typeof doc.authorization_endpoint !== 'string' || typeof doc.token_endpoint !== 'string') {
      throw new Error('Discovery document lacks the authorization or token endpoint.');
    }
    return doc as DiscoveryDocument;
  }

  private async postToken(fields: Record<string, string>): Promise<OidcTokenResponse> {
    const doc = await this.getDiscovery();
    const res = await this.http(doc.token_endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(fields).toString(),
    });
    if (!res.ok) throw new Error(`Token request failed (${res.status}).`);
    const body = (await res.json()) as Partial<OidcTokenResponse>;
    if (typeof body.access_token !== 'string' || body.access_token === '') {
      throw new Error('Token response has no access token.');
    }
    return body as OidcTokenResponse;
  }
}
