import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    watch: {
      usePolling: true,
      interval: 1000,
      ignored: ['**/node_modules/**', '**/.git/**', '**/storybook-static/**', '**/.venv/**'],
    },
  },
});
