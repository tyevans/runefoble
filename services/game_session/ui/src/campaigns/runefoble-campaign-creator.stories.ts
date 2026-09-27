import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-creator.ts';

const meta: Meta = {
  title: 'GameSession/CampaignCreator',
  component: 'runefoble-campaign-creator',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultOpen: Story = {
  render: () => html`
    <runefoble-campaign-creator
      .open=${true}
      title="Shadows of Drakkenheim"
      setting="Gothic Fantasy"
      system="5e"
      description="An urban ruin campaign featuring cosmic horror, lethal contamination, and competing factions."
    ></runefoble-campaign-creator>
  `,
};

export const EmptyForm: Story = {
  render: () => html`
    <runefoble-campaign-creator
      .open=${true}
    ></runefoble-campaign-creator>
  `,
};

export const WithValidationError: Story = {
  render: () => html`
    <runefoble-campaign-creator
      .open=${true}
      errorMessage="A campaign with this title already exists in your workspace."
    ></runefoble-campaign-creator>
  `,
};

export const SubmittingState: Story = {
  render: () => html`
    <runefoble-campaign-creator
      .open=${true}
      title="The Sunken Spire"
      setting="Underdark Exploration"
      system="pf2e"
      .submitting=${true}
    ></runefoble-campaign-creator>
  `,
};
