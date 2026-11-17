/**
 * Error types that the HTTP and WebSocket layers map to status codes.
 */

export class DomainError extends Error {
  constructor(
    message: string,
    readonly statusCode: 400 | 403 | 404 = 400
  ) {
    super(message);
    this.name = 'DomainError';
  }
}

/** A required dependency (Redis Streams or PostgreSQL) cannot serve the request now. */
export class DependencyUnavailableError extends Error {
  readonly statusCode = 503;

  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = 'DependencyUnavailableError';
  }
}
