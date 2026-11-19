/**
 * Entrypoint for services/audience_studio service. `main()` reads every setting, not module load,
 * so a missing value fails start-up with one error.
 */

import { createAdapters } from './adapters.js';
import { readSpicedbEndpoint, readSpicedbPresharedKey, readStoreSettings, readZitadelSettings } from './config.js';
import { createSpiceDbClient } from './spicedb/spicedbClient.js';
import { buildServer } from './server.js';

async function main() {
  const env = process.env;
  const port = parseInt(env.PORT || '8010', 10);
  const host = env.HOST || '0.0.0.0';
  const spicedbEndpoint = readSpicedbEndpoint(env);
  const spicedbKey = readSpicedbPresharedKey(env);
  const zitadel = readZitadelSettings(env);
  const stores = readStoreSettings(env);

  const { server } = await buildServer({
    spicedb: createSpiceDbClient({ endpoint: spicedbEndpoint, presharedKey: spicedbKey }),
    zitadel,
    logger: true,
    createAdapters: (log) => createAdapters(stores, log),
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
    await server.listen({ port, host });
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Failed to start Audience Studio:', err);
  process.exit(1);
});
