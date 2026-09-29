import { defineConfig } from 'vite';

const gatewayUrl = process.env.GATEWAY_API_URL || 'http://localhost:8000';
const gatewayWsUrl = process.env.GATEWAY_WS_URL || gatewayUrl.replace(/^http/, 'ws');
const mailpitUrl = process.env.MAILPIT_URL || 'http://localhost:8025';
const zitadelUrl = process.env.ZITADEL_URL || 'http://localhost:8080';

export default defineConfig({
  server: {
    host: '0.0.0.0',
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
        configure: (proxy) => {
          proxy.on('error', (err: Error) => {
            // Reconnect tolerance for WebSocket proxy in local dev
            console.debug('[vite-proxy] WS proxy connection event:', err.message);
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
      '/redoc': {
        target: gatewayUrl,
        changeOrigin: true,
      },
      '/campaigns': {
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
