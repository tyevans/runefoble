import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-dm-whisper-bar.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleDmWhisperBar',
  component: 'runefoble-dm-whisper-bar',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      sessionId="sess-101"
      campaignId="camp-202"
    ></runefoble-dm-whisper-bar>
  `,
};

export const WithPendingAction: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      sessionId="sess-101"
      campaignId="camp-202"
      pauseWindowMs="4000"
      .pendingAction=${{
        action_id: 'act-goblin-flank',
        actor_name: 'Goblin Skulker',
        action_type: 'move_and_strike',
        description: 'Disengages from Valeros and dashes behind Merisiel with jagged dagger drawn.',
        target: 'Merisiel',
        parameters: { damage: 5, advantage: true },
        pause_window_ms: 4000,
      }}
      .whispers=${[
        {
          whisper_id: 'whisp-1',
          whisper_type: 'monster_tactics',
          content: 'Goblin Skulkers gain sneak attack if allies are within 5 feet of target.',
        },
        {
          whisper_id: 'whisp-2',
          whisper_type: 'passive_perception',
          content: 'Ezren passive perception 15 notices the scent of goblin oil poison.',
        },
        {
          whisper_id: 'whisp-3',
          whisper_type: 'atmospheric_hint',
          content: 'The torch flickering reveals long spiderwebs hanging above.',
        },
      ]}
    ></runefoble-dm-whisper-bar>
  `,
};

export const BossEncounterSecrets: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      sessionId="sess-boss"
      campaignId="camp-202"
      .pendingAction=${{
        action_id: 'act-dragon-breath',
        actor_name: 'Young Red Dragon',
        action_type: 'breath_weapon',
        description: 'Inhales deeply, preparing to unleash a 30ft cone of searing flame across the bridge.',
        target: 'Party Frontline',
        parameters: { damage_dice: '16d6', dc: 17 },
        pause_window_ms: 6000,
      }}
      .whispers=${[
        {
          whisper_id: 'whisp-b1',
          whisper_type: 'monster_tactics',
          content: 'The dragon aims breath weapon at bridge choke point to maximize party casualties.',
        },
        {
          whisper_id: 'whisp-b2',
          whisper_type: 'narrative_secret',
          content: 'The dragon carries an old scar on its underbelly that Evelyn can use for a critical vulnerability hint.',
        },
        {
          whisper_id: 'whisp-b3',
          whisper_type: 'passive_perception',
          content: 'Passive Perception 16 hears the collapsing support beams under the bridge.',
        },
      ]}
    ></runefoble-dm-whisper-bar>
  `,
};
