/**
 * Entrypoint for services/audience_studio service.
 */

import { buildServer } from './server.js';

const PORT = parseInt(process.env.PORT || '8010', 10);
const HOST = process.env.HOST || '0.0.0.0';
const REDIS_URL = process.env.REDIS_URL || process.env.RUNEFOBLE_REDIS_URL;
const SPICEDB_ENDPOINT = process.env.RUNEFOBLE_SPICEDB_ENDPOINT;
const SPICEDB_TOKEN = process.env.SPICEDB_PRESHARED_KEY || 'runefoble_secret_key';

async function main() {
  const { server } = await buildServer({
    redisUrl: REDIS_URL,
    spicedbEndpoint: SPICEDB_ENDPOINT,
    spicedbToken: SPICEDB_TOKEN,
    logger: true,
  });

  const shutdown = async () => {
    try {
      await server.close();
      process.exit(0);
    } catch {
      process.exit(1);
    }
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);

  try {
    await server.listen({ port: PORT, host: HOST });
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Failed to start Audience Studio:', err);
  process.exit(1);
});

export { buildServer };
