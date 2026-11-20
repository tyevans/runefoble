import type { Meta, StoryObj } from '@storybook/web-components';
import { html, type TemplateResult } from 'lit';
import * as AbsenteeStories from './runefoble-absentee-directive.stories.ts';
import * as AutonomousDmStories from './autonomous-dm.stories.ts';
import * as WhisperStories from './dm-whisper-bar.stories.ts';
import * as EspionageStories from './runefoble-faction-espionage.stories.ts';
import * as RadarStories from './runefoble-faction-radar.stories.ts';

/**
 * Light and dark contrast check for The Watcher components (TASK-0763).
 * Each component renders twice, in a light and a dark container of the same theme.
 * The components hold no hex colours, so every colour comes from the theme tokens.
 */
const meta: Meta = {
  title: 'Design System/WatcherContrastMatrix',
  parameters: { layout: 'padded' },
  argTypes: {
    theme: {
      control: 'select',
      options: ['bauhaus', 'dark-fantasy', 'parchment', 'cyber-rune'],
    },
  },
  args: { theme: 'bauhaus' },
};

export default meta;
type Story = StoryObj<{ theme: string }>;

const renderStory = (story: StoryObj): TemplateResult =>
  (story.render as () => TemplateResult)();

const panel = (theme: string, mode: 'light' | 'dark', content: TemplateResult) => html`
  <div
    data-theme=${theme}
    data-color-mode=${mode}
    style="background: var(--rf-bg-canvas); color: var(--rf-text-primary); padding: 16px; border: var(--rf-border-width) solid var(--rf-border-color);"
  >
    <h3 style="margin-top: 0; font-size: 0.9rem; text-transform: uppercase;">${mode} mode</h3>
    ${content}
  </div>
`;

const matrix = (theme: string, content: TemplateResult) => html`
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start;">
    ${panel(theme, 'light', content)} ${panel(theme, 'dark', content)}
  </div>
`;

export const FactionRadar: Story = {
  render: ({ theme }) => matrix(theme, renderStory(RadarStories.DMPrivateBriefing)),
};

export const FactionEspionage: Story = {
  render: ({ theme }) => matrix(theme, renderStory(EspionageStories.DMPrivateBriefing)),
};

export const AbsenteeDirective: Story = {
  render: ({ theme }) => matrix(theme, renderStory(AbsenteeStories.Default)),
};

export const DmWhisperBar: Story = {
  render: ({ theme }) => matrix(theme, renderStory(WhisperStories.PendingAction)),
};

export const AutonomousDm: Story = {
  render: ({ theme }) => matrix(theme, renderStory(AutonomousDmStories.CryptAmbush)),
};
