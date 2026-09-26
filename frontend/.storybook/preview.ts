import type { Preview } from '@storybook/web-components-vite';
import '../src/styles/themes.css';

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
  },
  globalTypes: {
    theme: {
      name: 'Theme',
      description: 'Global theme for components',
      defaultValue: 'bauhaus',
      toolbar: {
        icon: 'paintbrush',
        items: [
          { value: 'bauhaus', title: 'Bauhaus Modernist' },
          { value: 'dark-fantasy', title: 'Dark Fantasy' },
          { value: 'parchment', title: 'Parchment' },
          { value: 'cyber-rune', title: 'Cyber Rune' },
        ],
        showName: true,
      },
    },
    colorMode: {
      name: 'Color Mode',
      description: 'Color mode (light / dark / system)',
      defaultValue: 'light',
      toolbar: {
        icon: 'circlehollow',
        items: [
          { value: 'light', title: 'Light Mode', icon: 'sun' },
          { value: 'dark', title: 'Dark Mode', icon: 'moon' },
          { value: 'system', title: 'System', icon: 'browser' },
        ],
        showName: true,
      },
    },
  },
  decorators: [
    (story, context) => {
      const theme = context.globals.theme || 'bauhaus';
      const colorMode = context.globals.colorMode || 'light';
      if (typeof document !== 'undefined' && document.documentElement) {
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-color-mode', colorMode);
      }
      return story();
    },
  ],
};

export default preview;
