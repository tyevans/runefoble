/**
 * The logger shape that adapters and services use. Fastify's logger satisfies it.
 */

import type { FastifyBaseLogger } from 'fastify';

export type Logger = Pick<FastifyBaseLogger, 'info' | 'warn' | 'error'>;
