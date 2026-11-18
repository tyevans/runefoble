/**
 * Fastify server factory for Audience Studio.
 * Governed by ADR-0005, ADR-0013, and Hard Invariant 5.
 */

import cors from '@fastify/cors';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import websocket from '@fastify/websocket';
import Fastify, { type FastifyInstance } from 'fastify';
import { AudienceAccess } from './access/audienceAccess.js';
import { ApprovalQueue } from './approvalQueue.js';
import type { Adapters } from './adapters.js';
import { principalOf } from './identity/principal.js';
import { registerIdentityHook } from './identity/identityHook.js';
import { type ZitadelSettings, ZitadelVerifier } from './identity/zitadelVerifier.js';
import { KeyedMutex } from './eventSourcing/keyedMutex.js';
import { AudienceEventRepository } from './eventSourcing/repository.js';
import { OutboxRelay } from './eventSourcing/outboxRelay.js';
import type { Logger } from './logger.js';
import { PollEngine } from './pollEngine.js';
import { createAudienceRoutes } from './routes.js';
import type { StreamPublisher } from './streamPublisher.js';
import type { EventStore } from './eventStore/types.js';
import type { SpiceDbPort } from './spicedb/spicedbPort.js';
import { WebSocketManager } from './websocket.js';

export interface ServerOptions {
  /** Authorization port. Production passes the SpiceDB gRPC client. Tests pass a fake at this boundary. */
  spicedb: SpiceDbPort;
  /** Zitadel issuer, audience, and optional JWKS URL. Every route verifies tokens against them. */
  zitadel: ZitadelSettings;
  logger?: boolean;
  /** Supplies the event store and stream publisher. Production passes createAdapters. */
  createAdapters: (log: Logger) => Promise<Adapters>;
  /** How often the outbox relay retries unsent events, in milliseconds. Defaults to one second. */
  outboxIntervalMs?: number;
}

const DEFAULT_OUTBOX_INTERVAL_MS = 1000;

export interface AppContext {
  server: FastifyInstance;
  pollEngine: PollEngine;
  approvalQueue: ApprovalQueue;
  access: AudienceAccess;
  eventStore: EventStore;
  streamPublisher: StreamPublisher;
  wsManager: WebSocketManager;
}

export async function buildServer(options: ServerOptions): Promise<AppContext> {
  const server = Fastify({
    logger: options.logger ?? false,
  });
  const log = server.log;

  // Resolves the signing keys before the first request. Fails start-up when discovery fails.
  const verifier = await ZitadelVerifier.create(options.zitadel);
  registerIdentityHook(server, verifier);

  const { eventStore, streamPublisher } = await options.createAdapters(log);
  // Fails start-up when the database is unreachable (ADR-0015 decision f).
  await eventStore.init();

  const access = new AudienceAccess(options.spicedb);
  const relay = new OutboxRelay(
    eventStore,
    streamPublisher,
    log,
    options.outboxIntervalMs ?? DEFAULT_OUTBOX_INTERVAL_MS
  );
  relay.start();
  const repo = new AudienceEventRepository(eventStore, relay);
  const mutex = new KeyedMutex();
  const approvalQueue = new ApprovalQueue(access, repo, mutex, log);
  const pollEngine = new PollEngine(repo, mutex, approvalQueue, access, log);
  const wsManager = new WebSocketManager(pollEngine, approvalQueue, access, log);

  server.addHook('onClose', async () => {
    pollEngine.close();
    relay.stop();
    await streamPublisher.close();
    await eventStore.close();
  });

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

  // 3. WebSockets. Accept only the Runefoble subprotocol. Never echo the bearer subprotocol.
  await server.register(websocket, {
    options: {
      handleProtocols: (protocols) => (protocols.has('runefoble.v1') ? 'runefoble.v1' : false),
    },
  });

  // Health and readiness probes. Readiness fails while Redis or the database is unavailable.
  server.get('/healthz', async () => ({ status: 'ok', service: 'audience_studio' }));
  server.get('/readyz', async (_request, reply) => {
    const [streamsUp, storeUp] = await Promise.all([streamPublisher.ping(), eventStore.ping()]);
    if (streamsUp && storeUp) {
      return { status: 'ready', service: 'audience_studio' };
    }
    return reply.code(503).send({
      status: 'unavailable',
      service: 'audience_studio',
      dependencies: { redis_streams: streamsUp, event_store: storeUp },
    });
  });

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

  // WebSocket Route for Live DM Approval & Audience Updates. The handshake needs campaign view (TASK-0554).
  server.get<{ Params: { campaignId: string } }>(
    '/ws/audience/:campaignId',
    {
      websocket: true,
      preHandler: async (req) => {
        await access.requireCampaign(principalOf(req), req.params.campaignId, 'view');
      },
    },
    (socket, req) => {
      wsManager.handleConnection(socket, req.params.campaignId, principalOf(req));
    }
  );

  // Register REST API routes
  await server.register(
    createAudienceRoutes({ pollEngine, approvalQueue }),
    { prefix: '/api/v1/audience' }
  );

  // Rebuild open polls and their timers from the event store.
  await pollEngine.restore();

  return { server, pollEngine, approvalQueue, access, eventStore, streamPublisher, wsManager };
}
