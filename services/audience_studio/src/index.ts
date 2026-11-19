/**
 * Entrypoint for services/audience_studio service.
 */

import { createAdapters } from './adapters.js';
import { readSpicedbEndpoint, readSpicedbPresharedKey, readStoreSettings, readZitadelSettings } from './config.js';
import { createSpiceDbClient } from './spicedb/spicedbClient.js';
import { buildServer } from './server.js';

const PORT = parseInt(process.env.PORT || '8010', 10);
const HOST = process.env.HOST || '0.0.0.0';
const SPICEDB_ENDPOINT = readSpicedbEndpoint(process.env);
const SPICEDB_TOKEN = readSpicedbPresharedKey(process.env);
const ZITADEL = readZitadelSettings(process.env);
const STORES = readStoreSettings(process.env);

async function main() {
  const { server } = await buildServer({
    spicedb: createSpiceDbClient({ endpoint: SPICEDB_ENDPOINT, presharedKey: SPICEDB_TOKEN }),
    zitadel: ZITADEL,
    logger: true,
    createAdapters: (log) => createAdapters(STORES, log),
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
