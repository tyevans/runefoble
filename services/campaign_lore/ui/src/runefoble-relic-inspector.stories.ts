import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-relic-inspector.ts';
import type { RelicRune } from './runefoble-relic-inspector.ts';

const meta: Meta = {
  title: 'CampaignLore/RunefobleRelicInspector',
  component: 'runefoble-relic-inspector',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleRunes: RelicRune[] = [
  {
    id: 'rune-spire-1',
    inscription: 'Khar-Drak-Mor',
    position: [0.0, 0.35, -0.15],
    translated: 'By Blood Sealed',
  },
  {
    id: 'rune-spire-2',
    inscription: 'Val-Teth-Azul',
    position: [-0.25, -0.1, -0.12],
    translated: 'The Spire Slumbers Beneath Deep Waters',
  },
];

export const AmuletOfTheSunkenSpire: Story = {
  render: () => html`
    <runefoble-relic-inspector
      relicName="Amulet of the Sunken Spire"
      relicType="amulet"
      modelGeometry="amulet_sunken_spire"
      .metallic=${0.88}
      .roughness=${0.22}
      emissiveColor="#00ffcc"
      .runes=${sampleRunes}
    ></runefoble-relic-inspector>
  `,
};

export const DaggerOfTheShadowWeave: Story = {
  render: () => html`
    <runefoble-relic-inspector
      relicName="Dagger of the Shadow Weave"
      relicType="dagger"
      modelGeometry="dagger_shadow_weave"
      .metallic=${0.95}
      .roughness=${0.15}
      emissiveColor="#a855f7"
      .runes=${[
        {
          id: 'rune-dagger-1',
          inscription: 'Nox-Siphon',
          position: [0.0, 0.5, 0.05],
          translated: 'Drink the Unseen Light',
        },
      ]}
    ></runefoble-relic-inspector>
  `,
};

export const CelestialChronoSphere: Story = {
  render: () => html`
    <runefoble-relic-inspector
      relicName="Celestial Chrono-Sphere"
      relicType="puzzle_box"
      modelGeometry="puzzle_box_celestial"
      .metallic=${0.72}
      .roughness=${0.32}
      emissiveColor="#f59e0b"
      .runes=${[
        {
          id: 'rune-box-1',
          inscription: 'Aethel-Sol-Lux',
          position: [0.3, 0.0, 0.3],
          translated: 'Turn Three Rings When the Moon Weeps',
        },
      ]}
    ></runefoble-relic-inspector>
  `,
};
