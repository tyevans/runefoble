/**
 * Fastify server factory and configuration for Audience Studio.
 * Governed by ADR-0005, ADR-0013, and Hard Invariant 5.
 */

import cors from '@fastify/cors';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import websocket from '@fastify/websocket';
import Fastify, { type FastifyInstance } from 'fastify';
import { ApprovalQueue } from './approvalQueue.js';
import { ZanzibarClient } from './auth.js';
import { PollEngine } from './pollEngine.js';
import { RedisStreamsClient } from './redis.js';
import { createAudienceRoutes } from './routes.js';
import { WebSocketManager } from './websocket.js';

export interface ServerOptions {
  redisUrl?: string;
  spicedbEndpoint?: string;
  spicedbToken?: string;
  logger?: boolean;
}

export interface AppContext {
  server: FastifyInstance;
  pollEngine: PollEngine;
  approvalQueue: ApprovalQueue;
  auth: ZanzibarClient;
  redis: RedisStreamsClient;
  wsManager: WebSocketManager;
}

export async function buildServer(options: ServerOptions = {}): Promise<AppContext> {
  const server = Fastify({
    logger: options.logger ?? false,
  });

  const auth = new ZanzibarClient(
    options.spicedbEndpoint,
    options.spicedbToken
  );
  const redis = new RedisStreamsClient(options.redisUrl);
  const approvalQueue = new ApprovalQueue(auth, redis);
  const pollEngine = new PollEngine(redis, approvalQueue);
  const wsManager = new WebSocketManager(pollEngine, approvalQueue);

  // 1. CORS
  await server.register(cors, { origin: true });

  // 2. Swagger / OpenAPI documentation (Hard Invariant 5)
  await server.register(swagger, {
    openapi: {
      info: {
        title: 'Runefoble Audience Studio API',
        description: 'TypeScript Audience Studio & Live Stream Interactivity Service',
        version: '0.1.0',
      },
      servers: [{ url: 'http://localhost:8010' }],
      tags: [{ name: 'Audience', description: 'Live spectator chaos polls and modifiers' }],
    },
  });

  await server.register(swaggerUi, {
    routePrefix: '/docs',
  });

  // 3. WebSockets
  await server.register(websocket);

  // Health and Readiness probes
  server.get('/healthz', async () => ({ status: 'ok', service: 'audience_studio' }));
  server.get('/readyz', async () => ({ status: 'ready', service: 'audience_studio' }));

  // Microfrontend manifest (ADR-0013)
  server.get('/ui/manifest', async () => ({
    service: 'audience_studio',
    package: '@runefoble/audience-studio-ui',
    components: ['runefoble-audience-studio'],
    version: '0.1.0',
  }));

  // Expose /openapi.json explicitly
  server.get('/openapi.json', async () => {
    return server.swagger();
  });

  // WebSocket Route for Live DM Approval & Audience Updates
  server.get('/ws/audience/:campaignId', { websocket: true }, (socket, req) => {
    const { campaignId } = req.params as { campaignId: string };
    wsManager.handleConnection(socket, campaignId);
  });

  // Register REST API routes
  await server.register(
    createAudienceRoutes({ pollEngine, approvalQueue, auth }),
    { prefix: '/api/v1/audience' }
  );

  return { server, pollEngine, approvalQueue, auth, redis, wsManager };
}
