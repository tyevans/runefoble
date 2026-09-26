import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-stand-in-guardrails.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleStandInGuardrails',
  component: 'runefoble-stand-in-guardrails',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultGuardrails: Story = {
  render: () => html`
    <runefoble-stand-in-guardrails
      characterId="c-123"
      characterName="Kyra (Cleric)"
      .preserveSpellSlots=${{ 3: 1 }}
      .protectAllies=${['Marcus', 'Valeros']}
      .protectAllyHpThreshold=${0.3}
      .riskThreshold=${'cautious'}
      .avoidMelee=${true}
      .permadeathSafeguard=${true}
    ></runefoble-stand-in-guardrails>
  `,
};

export const AggressiveSafeguardOnly: Story = {
  render: () => html`
    <runefoble-stand-in-guardrails
      characterId="c-456"
      characterName="Valeros (Fighter)"
      .preserveSpellSlots=${{}}
      .protectAllies=${[]}
      .riskThreshold=${'reckless'}
      .avoidMelee=${false}
      .permadeathSafeguard=${true}
    ></runefoble-stand-in-guardrails>
  `,
};
