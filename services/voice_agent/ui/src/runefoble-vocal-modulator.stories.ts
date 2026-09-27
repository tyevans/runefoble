import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-vocal-modulator.ts';

const meta: Meta = {
  title: 'Voice/RunefobleVocalModulator',
  component: 'runefoble-vocal-modulator',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const wrap = (content: unknown) => html`
  <div style="padding: 24px; max-width: 480px; background: var(--rf-bg-canvas, #f4f4f5);">
    ${content}
  </div>
`;

export const DefaultBypassed: Story = {
  render: () => wrap(html`
    <runefoble-vocal-modulator .isEnabled=${false}></runefoble-vocal-modulator>
  `),
};

export const DragonActive: Story = {
  render: () => wrap(html`
    <runefoble-vocal-modulator
      .isEnabled=${true}
      activePreset="ancient-dragon"
      .pitchShift=${-7.0}
      .formantShift=${0.75}
      .resonanceHz=${140}
      .octaveOffset=${-0.5}
    ></runefoble-vocal-modulator>
  `),
};

export const GoblinActive: Story = {
  render: () => wrap(html`
    <runefoble-vocal-modulator
      .isEnabled=${true}
      activePreset="goblin-skulker"
      .pitchShift=${6.5}
      .formantShift=${1.4}
      .resonanceHz=${2800}
      .octaveOffset=${0.5}
    ></runefoble-vocal-modulator>
  `),
};

export const EtherealActive: Story = {
  render: () => wrap(html`
    <runefoble-vocal-modulator
      .isEnabled=${true}
      activePreset="celestial-spirit"
      .pitchShift=${3.0}
      .formantShift=${1.2}
      .resonanceHz=${1600}
      .octaveOffset=${0.25}
    ></runefoble-vocal-modulator>
  `),
};

export const RoboticActive: Story = {
  render: () => wrap(html`
    <runefoble-vocal-modulator
      .isEnabled=${true}
      activePreset="robotic-construct"
      .pitchShift=${-2.0}
      .formantShift=${0.95}
      .resonanceHz=${440}
      .octaveOffset=${0.0}
    ></runefoble-vocal-modulator>
  `),
};

export const AdvancedSlidersOpen: Story = {
  render: () => wrap(html`
    <runefoble-vocal-modulator
      .isEnabled=${true}
      activePreset="ancient-dragon"
      .showSliders=${true}
      .pitchShift=${-5.0}
      .formantShift=${0.8}
      .resonanceHz=${220}
      .octaveOffset=${-0.5}
    ></runefoble-vocal-modulator>
  `),
};

export const InteractiveSimulator: Story = {
  render: () => wrap(html`
    <runefoble-vocal-modulator
      sessionId="sess-demo-42"
      peerId="dm-narrator"
      .isEnabled=${false}
    ></runefoble-vocal-modulator>
  `),
};
