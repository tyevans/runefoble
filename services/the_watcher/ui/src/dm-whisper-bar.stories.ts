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

const GOBLIN_ACTION = {
  action_id: 'act-goblin-flank',
  actor_name: 'Goblin Skulker',
  action_type: 'move_and_strike',
  description: 'Disengages from Valeros and dashes behind Merisiel with jagged dagger drawn.',
  target: 'Merisiel',
  parameters: { damage: 5, advantage: true },
  status: 'pending',
  pause_window_ms: 4000,
};

const MODEL_WHISPERS = [
  {
    whisper_id: 'whisp-n1',
    whisper_type: 'narration',
    content: 'The torches gutter. Something breathes behind the sealed door.',
    metadata: { source: 'llm', suggested_dm_prompts: ['Ask who opens the door.'] },
  },
];

/** A new session: the bar has no whisper and no action. No story here calls a route. */
export const Empty: Story = {
  render: () => html`<runefoble-dm-whisper-bar></runefoble-dm-whisper-bar>`,
};

/** The narration port has no engine. The bar says so and shows no invented text. */
export const NoModel: Story = {
  render: () => html`<runefoble-dm-whisper-bar narrationEngine="none"></runefoble-dm-whisper-bar>`,
};

/** Whispers that the language model wrote. */
export const Whispers: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar narrationEngine="inference_worker" .whispers=${MODEL_WHISPERS}></runefoble-dm-whisper-bar>
  `,
};

/** An AI action waits in its pause window. The DM can approve, veto or edit it. */
export const PendingAction: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      narrationEngine="inference_worker"
      pauseWindowMs="4000"
      .pendingAction=${GOBLIN_ACTION}
      .whispers=${MODEL_WHISPERS}
    ></runefoble-dm-whisper-bar>
  `,
};

/** The veto route answered 200. The action shows as vetoed and has no control. */
export const Vetoed: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      narrationEngine="inference_worker"
      .pendingAction=${{ ...GOBLIN_ACTION, status: 'vetoed' }}
    ></runefoble-dm-whisper-bar>
  `,
};

export const AudienceNarrationToSend: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      .whispers=${[
        {
          whisper_id: 'whisp-aud-1',
          whisper_type: 'audience_narration',
          content: 'Fog rolls over the crypt steps and swallows the torchlight.',
          metadata: { dispatched: false, source_proposal_id: 'prop-fog', sensory_details: ['cold damp air'] },
        },
      ]}
    ></runefoble-dm-whisper-bar>
  `,
};

export const AudienceNarrationSent: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      .whispers=${[
        {
          whisper_id: 'whisp-aud-2',
          whisper_type: 'audience_narration',
          content: 'The bell tolls once. Every torch in the crypt gutters.',
          metadata: { dispatched: true, source_proposal_id: 'prop-bell' },
        },
      ]}
    ></runefoble-dm-whisper-bar>
  `,
};

export const NarrationUnavailable: Story = {
  render: () => html`
    <runefoble-dm-whisper-bar
      .whispers=${[
        {
          whisper_id: 'whisp-unavail-1',
          whisper_type: 'narration_unavailable',
          content: 'The inference worker did not return narration for this modifier.',
          metadata: { source_proposal_id: 'prop-storm', modifier_type: 'weather_change' },
        },
      ]}
    ></runefoble-dm-whisper-bar>
  `,
};
