import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../components/runefoble-spectator-view.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleSpectatorView',
  component: 'runefoble-spectator-view',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const LiveEncounterStream: Story = {
  render: () => html`
    <runefoble-spectator-view
      sessionId="camp-4-encounter-12"
      .cols=${8}
      .rows=${8}
      .round=${3}
      .tokens=${[
        { id: 't1', name: 'Valeros', x: 2, y: 3, color: '#2563eb', conditions: ['Blessed'], isActiveTurn: true },
        { id: 't2', name: 'Kyra', x: 3, y: 3, color: '#db2777', isAiControlled: true, conditions: ['Drunk'] },
        { id: 't3', name: 'Bugbear', x: 5, y: 3, color: '#e63946', conditions: [] },
        { id: 't4', name: 'Skeleton', x: 6, y: 2, color: '#e63946', conditions: [] },
      ]}
      .atmosphere=${{
        location_name: 'Crypt of the Restless Kings',
        lighting: 'Flickering wall torches casting deep shadows',
        mood: 'Deadly Encounter',
        description: 'Dust and dry bone splinters scatter across the stone floor as the Bugbear raises its morningstar.',
        ambient_audio_prompt: 'dull clatter of bones, heavy breathing, tension strings',
      }}
      .chronicle=${[
        {
          id: 'c1',
          speaker: 'Valeros',
          text: 'I step forward into defensive stance, raising my shield!',
          timestamp: '20:14:02',
          action_type: 'speech',
        },
        {
          id: 'c2',
          speaker: 'Kyra (AI Stand-in)',
          text: 'May the Sun Maiden burn these wretched bones! (Hic!)',
          timestamp: '20:14:15',
          action_type: 'speech',
        },
        {
          id: 'c3',
          speaker: 'The Watcher',
          text: 'The Bugbear roars, charging toward Valeros!',
          timestamp: '20:14:30',
          action_type: 'dm_ruling',
        },
      ]}
    ></runefoble-spectator-view>
  `,
};

export const AtmosphericExploration: Story = {
  render: () => html`
    <runefoble-spectator-view
      sessionId="camp-4-exploration-8"
      .cols=${8}
      .rows=${8}
      .round=${1}
      .tokens=${[
        { id: 't1', name: 'Valeros', x: 1, y: 4, color: '#2563eb' },
        { id: 't2', name: 'Kyra', x: 2, y: 4, color: '#db2777', isAiControlled: true },
      ]}
      .atmosphere=${{
        location_name: 'The Sunken Scriptorium',
        lighting: 'Shimmering azure luminescence from submerged arcane glass',
        mood: 'Mysterious',
        description: 'Half-submerged pedestals hold stone codices preserved by ancient wards. Ripples echo through vaulted corridors.',
        ambient_audio_prompt: 'gentle water ripples, distant crystalline chimes, solemn echoing drip',
      }}
      .chronicle=${[
        {
          id: 'c1',
          speaker: 'The Watcher',
          text: 'The party steps into knee-deep water. Faint runes pulse beneath the surface.',
          timestamp: '19:02:10',
          action_type: 'narration',
        },
        {
          id: 'c2',
          speaker: 'Valeros',
          text: 'Keep your eyes on the ceiling. Water this clear hides things.',
          timestamp: '19:02:45',
          action_type: 'speech',
        },
      ]}
    ></runefoble-spectator-view>
  `,
};
