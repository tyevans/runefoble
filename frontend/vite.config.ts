import { defineConfig } from 'vite';

const gatewayUrl = process.env.GATEWAY_API_URL || 'http://localhost:8000';
const gatewayWsUrl = process.env.GATEWAY_WS_URL || gatewayUrl.replace(/^http/, 'ws');
const mailpitUrl = process.env.MAILPIT_URL || 'http://localhost:8025';
const zitadelUrl = process.env.ZITADEL_URL || 'http://localhost:8080';

export default defineConfig({
  server: {
    watch: {
      usePolling: true,
      interval: 1000,
      ignored: ['**/node_modules/**', '**/.git/**', '**/storybook-static/**', '**/.venv/**'],
    },
    proxy: {
      '/api/v1': {
        target: gatewayUrl,
        changeOrigin: true,
      },
      '/api': {
        target: gatewayUrl,
        changeOrigin: true,
      },
      '/ws': {
        target: gatewayWsUrl,
        ws: true,
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err: Error) => {
            console.warn('[vite-proxy] WebSocket proxy error:', err.message);
          });
        },
      },
      '/docs': {
        target: gatewayUrl,
        changeOrigin: true,
      },
      '/openapi.json': {
        target: gatewayUrl,
        changeOrigin: true,
      },
      '/mail': {
        target: mailpitUrl,
        changeOrigin: true,
      },
      '/mailpit': {
        target: mailpitUrl,
        changeOrigin: true,
      },
      '/oauth': {
        target: zitadelUrl,
        changeOrigin: true,
      },
      '/auth': {
        target: zitadelUrl,
        changeOrigin: true,
      },
      '/healthz': {
        target: gatewayUrl,
        changeOrigin: true,
      },
    },
  },
});
