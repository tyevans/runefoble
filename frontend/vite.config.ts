import { defineConfig } from 'vite';

const gatewayUrl = process.env.GATEWAY_API_URL || 'http://localhost:8000';
const gatewayWsUrl = process.env.GATEWAY_WS_URL || gatewayUrl.replace(/^http/, 'ws');

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
      '/ws': {
        target: gatewayWsUrl,
        ws: true,
      },
    },
  },
});
