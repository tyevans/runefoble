import type { StorybookConfig } from '@storybook/web-components-vite';

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  addons: ['@storybook/addon-essentials'],
  framework: {
    name: '@storybook/web-components-vite',
    options: {},
  },
  async viteFinal(config) {
    config.server = {
      ...config.server,
      watch: {
        usePolling: true,
        interval: 1000,
        ignored: ['**/node_modules/**', '**/.git/**', '**/storybook-static/**', '**/.venv/**'],
      },
    };
    return config;
  },
};

export default config;
