import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-wardrobe-gallery.ts';

const sampleVariants = [
  {
    variantId: 'var-nadia-base',
    variantName: 'Adventurer Tunic',
    attireType: 'base',
    imageUrl:
      'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%232a9d8f"/><circle cx="50" cy="38" r="18" fill="%23f4a261"/><rect x="25" y="60" width="50" height="36" rx="10" fill="%23e76f51"/></svg>',
  },
  {
    variantId: 'var-nadia-gala',
    variantName: 'Masquerade Gown',
    attireType: 'ballroom_masquerade',
    imageUrl:
      'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%23d4af37"/><circle cx="50" cy="38" r="18" fill="%23f4a261"/><rect x="25" y="60" width="50" height="36" rx="10" fill="%237209b7"/></svg>',
  },
  {
    variantId: 'var-nadia-tundra',
    variantName: 'Arctic Frost Cowl',
    attireType: 'arctic_tundra',
    imageUrl:
      'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%23a8dadc"/><circle cx="50" cy="38" r="18" fill="%23f4a261"/><rect x="25" y="60" width="50" height="36" rx="10" fill="%231d3557"/></svg>',
  },
];

const meta: Meta = {
  title: 'TTRPG/RunefobleWardrobeGallery',
  component: 'runefoble-wardrobe-gallery',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const HealthyBase: Story = {
  render: () => html`
    <runefoble-wardrobe-gallery
      characterId="char-nadia-001"
      characterName="Nadia the Expressive Bard"
      .currentHp=${34}
      .maxHp=${34}
      activePortraitUrl="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%232a9d8f'/><circle cx='50' cy='38' r='18' fill='%23f4a261'/><rect x='25' y='60' width='50' height='36' rx='10' fill='%23e76f51'/></svg>"
      activeVariantId="var-nadia-base"
      .variants=${sampleVariants}
      .conditionBadges=${[]}
    ></runefoble-wardrobe-gallery>
  `,
};

export const BloodiedInjury: Story = {
  render: () => html`
    <runefoble-wardrobe-gallery
      characterId="char-nadia-001"
      characterName="Nadia the Expressive Bard"
      .currentHp=${12}
      .maxHp=${34}
      activePortraitUrl="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23700000'/><circle cx='50' cy='38' r='18' fill='%23f4a261'/><rect x='25' y='60' width='50' height='36' rx='10' fill='%23b30000'/><circle cx='50' cy='50' r='46' stroke='%23e63946' stroke-width='4' fill='none'/></svg>"
      activeVariantId="var-nadia-base"
      .variants=${sampleVariants}
      .conditionBadges=${['bloodied']}
    ></runefoble-wardrobe-gallery>
  `,
};

export const PoisonedAffliction: Story = {
  render: () => html`
    <runefoble-wardrobe-gallery
      characterId="char-nadia-001"
      characterName="Nadia the Expressive Bard"
      .currentHp=${28}
      .maxHp=${34}
      activePortraitUrl="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%231b8a36'/><circle cx='50' cy='38' r='18' fill='%23f4a261'/><rect x='25' y='60' width='50' height='36' rx='10' fill='%2300f5d4'/><circle cx='50' cy='50' r='44' stroke='%2300f5d4' stroke-width='4' stroke-dasharray='6 4' fill='none'/></svg>"
      activeVariantId="var-nadia-base"
      .variants=${sampleVariants}
      .conditionBadges=${['poisoned']}
    ></runefoble-wardrobe-gallery>
  `,
};

export const GalaAttireMasquerade: Story = {
  render: () => html`
    <runefoble-wardrobe-gallery
      characterId="char-nadia-001"
      characterName="Nadia the Expressive Bard"
      .currentHp=${34}
      .maxHp=${34}
      activePortraitUrl="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='48' fill='%23d4af37'/><circle cx='50' cy='38' r='18' fill='%23f4a261'/><rect x='25' y='60' width='50' height='36' rx='10' fill='%237209b7'/><circle cx='50' cy='50' r='46' stroke='%23ffd700' stroke-width='4' fill='none'/></svg>"
      activeVariantId="var-nadia-gala"
      .variants=${sampleVariants}
      .conditionBadges=${[]}
    ></runefoble-wardrobe-gallery>
  `,
};
