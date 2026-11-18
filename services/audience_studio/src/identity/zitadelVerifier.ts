/**
 * Verifies Zitadel access tokens. Same contract as libs/runefoble_auth/src/runefoble_auth/zitadel.py
 * (TASK-0533, ADR-0015 decision c). Every check is mandatory. No setting disables one.
 *
 * - RS256 signature only, against the issuer's JWKS.
 * - Required claims: exp, sub, iss, aud. Issuer and audience must match exactly.
 * - The verified `sub` is the principal. Roles and other claims grant nothing.
 */

import { createRemoteJWKSet, errors as joseErrors, jwtVerify, type JWTPayload } from 'jose';
import { DependencyUnavailableError } from '../errors.js';

export interface ZitadelSettings {
  issuer: string;
  audience: string;
  /** Optional. When unset, the verifier reads `jwks_uri` from OIDC discovery at start-up. */
  jwksUrl?: string;
}

/** The identity a verified token proves. */
export interface VerifiedPrincipal {
  userId: string;
  username: string;
  email?: string;
}

/** The token is not valid for this service. The caller answers 401. */
export class TokenRejectedError extends Error {
  constructor(reason: string) {
    super(reason);
    this.name = 'TokenRejectedError';
  }
}

const ACCEPTED_ALGORITHMS = ['RS256'];
const REQUIRED_CLAIMS = ['exp', 'sub', 'iss', 'aud'];
const DISCOVERY_TIMEOUT_MS = 5000;

/** Errors that mean the token itself is bad. Any other failure means the key source is down. */
const TOKEN_ERRORS = [
  joseErrors.JWSInvalid,
  joseErrors.JWTInvalid,
  joseErrors.JWTClaimValidationFailed,
  joseErrors.JWTExpired,
  joseErrors.JWSSignatureVerificationFailed,
  joseErrors.JOSEAlgNotAllowed,
  joseErrors.JWKSNoMatchingKey,
  joseErrors.JWKSMultipleMatchingKeys,
];

/** Reads `jwks_uri` from the issuer's OIDC discovery document. Throws when discovery fails. */
export async function discoverJwksUrl(issuer: string): Promise<string> {
  const url = `${issuer.replace(/\/+$/, '')}/.well-known/openid-configuration`;
  const res = await fetch(url, { signal: AbortSignal.timeout(DISCOVERY_TIMEOUT_MS) });
  if (!res.ok) {
    throw new Error(`OIDC discovery at ${url} returned HTTP ${res.status}`);
  }
  const document = (await res.json()) as { jwks_uri?: unknown };
  if (typeof document.jwks_uri !== 'string' || document.jwks_uri === '') {
    throw new Error(`OIDC discovery document at ${url} has no jwks_uri`);
  }
  return document.jwks_uri;
}

export class ZitadelVerifier {
  private constructor(
    private readonly settings: ZitadelSettings,
    private readonly keys: ReturnType<typeof createRemoteJWKSet>
  ) {}

  /** Resolves the JWKS URL (configured or discovered) once, at start-up. */
  static async create(settings: ZitadelSettings): Promise<ZitadelVerifier> {
    const jwksUrl = settings.jwksUrl ?? (await discoverJwksUrl(settings.issuer));
    return new ZitadelVerifier(settings, createRemoteJWKSet(new URL(jwksUrl)));
  }

  /**
   * Returns the principal for a valid token.
   * @throws TokenRejectedError when the token fails any check.
   * @throws DependencyUnavailableError when the signing keys cannot be fetched.
   */
  async verify(token: string): Promise<VerifiedPrincipal> {
    let payload: JWTPayload;
    try {
      ({ payload } = await jwtVerify(token, this.keys, {
        issuer: this.settings.issuer,
        audience: this.settings.audience,
        algorithms: ACCEPTED_ALGORITHMS,
        requiredClaims: REQUIRED_CLAIMS,
      }));
    } catch (err) {
      if (TOKEN_ERRORS.some((kind) => err instanceof kind)) {
        throw new TokenRejectedError((err as Error).message);
      }
      throw new DependencyUnavailableError('Zitadel signing keys are unavailable', { cause: err });
    }
    return principalFromClaims(payload);
  }
}

function principalFromClaims(payload: JWTPayload): VerifiedPrincipal {
  if (typeof payload.sub !== 'string' || payload.sub === '') {
    throw new TokenRejectedError("Token 'sub' claim is empty or not a string");
  }
  const username = typeof payload.preferred_username === 'string' && payload.preferred_username
    ? payload.preferred_username
    : payload.sub;
  const email = typeof payload.email === 'string' && payload.email ? payload.email : undefined;
  return { userId: payload.sub, username, email };
}
