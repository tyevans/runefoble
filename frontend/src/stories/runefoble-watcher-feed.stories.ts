import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../components/runefoble-watcher-feed.ts';
import type { WatcherFeedEvent } from '../components/runefoble-watcher-feed.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleWatcherFeed',
  component: 'runefoble-watcher-feed',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleEvents: WatcherFeedEvent[] = [
  {
    id: 'e1',
    timestamp: '19:42:01',
    source: 'watcher_dm',
    speaker: 'The Watcher (AI DM)',
    text: 'The torchlight flickers as the cavern walls reverberate with distant skittering. What do you do?',
    actionType: 'dm_ruling',
  },
  {
    id: 'e2',
    timestamp: '19:42:15',
    source: 'player',
    speaker: 'Valeros (Player Voice)',
    text: '"I draw my longsword and step cautiously towards the eastern tunnel."',
    actionType: 'speech',
  },
  {
    id: 'e3',
    timestamp: '19:42:18',
    source: 'system',
    speaker: 'Board State Engine',
    text: 'Valeros moved 2 hexes to (3, 3). Fog of war cleared in radius 4.',
    actionType: 'board_move',
  },
  {
    id: 'e4',
    timestamp: '19:42:25',
    source: 'stand_in',
    speaker: 'Kyra (AI Stand-in, Drunk)',
    text: '"Hic! Stand back, Valeros! The dawnflower guides my clumsy mace!" Kyra stumbles 1 square ahead.',
    actionType: 'speech',
  },
];

export const ActiveSessionStream: Story = {
  render: () => html`
    <runefoble-watcher-feed .events=${sampleEvents}></runefoble-watcher-feed>
  `,
};
