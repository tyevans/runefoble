import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-command-bar.ts';
import type { CommandBarStatus } from './command-bar-body.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCommandBar',
  component: 'runefoble-command-bar',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

/** A bar for Valeros, whose token stands at (4, 2) on a 10 x 10 board. */
function bar(status: CommandBarStatus, tokenId: string | null = 'tok-valeros') {
  return html`
    <runefoble-command-bar
      .sessionId=${'session-tomb-14'}
      .campaignId=${'campaign-4'}
      .speakerId=${'char-valeros'}
      .speakerName=${'Valeros the Bold'}
      .tokenId=${tokenId}
      .fromX=${tokenId ? 4 : null}
      .fromY=${tokenId ? 2 : null}
      .gridCols=${10}
      .gridRows=${10}
      .status=${status}
    ></runefoble-command-bar>
  `;
}

export const Idle: Story = { render: () => bar({ kind: 'idle' }) };

export const NoToken: Story = { render: () => bar({ kind: 'idle' }, null) };

export const Sending: Story = { render: () => bar({ kind: 'sending' }) };

export const Reply: Story = {
  render: () => bar({ kind: 'reply', text: 'Valeros the Bold moves 2 squares west. Confirm the move on the board.' }),
};

export const NotUnderstood: Story = { render: () => bar({ kind: 'reply', text: 'Not understood.' }) };

export const CallFailed: Story = {
  render: () => bar({ kind: 'error', text: 'HTTP 503: The Watcher is unavailable.' }),
};
