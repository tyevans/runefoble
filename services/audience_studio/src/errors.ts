/**
 * Error types that the HTTP and WebSocket layers map to status codes.
 * Every HTTP-visible error extends HttpError. Text matching never selects a status (TASK-0554).
 */

export abstract class HttpError extends Error {
  abstract readonly statusCode: 400 | 401 | 403 | 404 | 409 | 503;

  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = new.target.name;
  }
}

/** A command or query breaks a domain rule, such as a duplicate vote. */
export class DomainError extends HttpError {
  readonly statusCode = 400;
}

/** The named poll or proposal does not exist. */
export class NotFound extends HttpError {
  readonly statusCode = 404;
}

/** The write lost a race with another writer on the same stream. The client may retry the command. */
export class ConflictError extends HttpError {
  readonly statusCode = 409;
}

/** The verified principal lacks the schema permission for the action. */
export class Forbidden extends HttpError {
  readonly statusCode = 403;
}

/** No verified principal is present. The identity hook answers most of these before a handler runs. */
export class Unauthenticated extends HttpError {
  readonly statusCode = 401;
}

/** A required dependency (Redis Streams, PostgreSQL, SpiceDB, or the JWKS endpoint) cannot serve the request now. */
export class DependencyUnavailableError extends HttpError {
  readonly statusCode = 503;
}
