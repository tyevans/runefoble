import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-board.ts';
import {
  expiringGhostPreview,
  sampleActiveEncounterTokens,
  sampleAoETemplates,
  sampleMultiplayerTokens,
  sampleTerrain,
  sampleTokens,
  spokenGhostPreview,
} from './runefoble-board.stories.fixtures.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleBoard',
  component: 'runefoble-board',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens}
      watcherStatus="Tracking 4 active tokens. Awaiting DM narration."></runefoble-board>
  `,
};

export const TokenKinematicsAndMeasurement: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain}
      watcherStatus="Drag any token to test tactile kinematics, 5-ft waypoint ruler, and terrain penalties."></runefoble-board>
  `,
};

export const SpokenGhostPreviewWithConfirmation: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain} .activeGhost=${spokenGhostPreview}
      watcherStatus="Speech Intent Parsed: 'Valeros charges 3 squares east'. Click ghost or Confirm to execute."></runefoble-board>
  `,
};

export const GhostCancellationAndTimeout: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain} .activeGhost=${expiringGhostPreview}
      watcherStatus="Ghost preview expiring in 4s. Tap Cancel to rollback or let timeout discard."></runefoble-board>
  `,
};

export const ActiveEncounter: Story = {
  render: () => html`
    <runefoble-board .cols=${10} .rows=${8} .tokens=${sampleActiveEncounterTokens} .terrainCells=${sampleTerrain}
      watcherStatus="Voice detected: 'Valeros charges 2 squares east!'"></runefoble-board>
  `,
};

export const FogOfWarEncounter: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} .fogOfWar=${true}
      watcherStatus="Fog of War shrouds unrevealed dungeon corridors."></runefoble-board>
  `,
};

export const ActiveTurn: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} activeTurnTokenId="1"
      watcherStatus="Active turn: Valeros (Fighter). 30 ft movement remaining."></runefoble-board>
  `,
};

export const MultiplayerTokens: Story = {
  render: () => html`
    <runefoble-board .cols=${10} .rows=${10} .fogOfWar=${true} activeTurnTokenId="2" .tokens=${sampleMultiplayerTokens}
      watcherStatus="Turn 4: Kyra (AI Stand-in) is deliberating tactical healing spell."></runefoble-board>
  `,
};

export const EvocationFirestormVFX: Story = {
  render: () => {
    const castFireball = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      board?.triggerSpellVFX({
        spellName: 'Fireball', spellArchetype: 'evocation',
        fromX: 2, fromY: 3, toX: 6, toY: 5, radiusFt: 20, damageType: 'fire',
      });
    };
    const advanceRounds = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      board?.particleEngine?.decayDecals(1);
      board?.requestUpdate();
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 12px; align-items: center;">
        <div style="display: flex; gap: 8px;">
          <button style="background: #dc2626; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;" @click=${castFireball}>
            🔥 Cast Fireball (Valeros -> Red Dragon)
          </button>
          <button style="background: #4b5563; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;" @click=${advanceRounds}>
            ⏳ Advance Round (Decay Scorched Decals)
          </button>
        </div>
        <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} watcherStatus="Nadia: 'I cast Fireball centered on the Red Dragon at (6, 5)!'"></runefoble-board>
      </div>
    `;
  },
};

export const EvocationLightningArcVFX: Story = {
  render: () => {
    const castLightning = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      board?.triggerSpellVFX({
        spellName: 'Lightning Bolt', spellArchetype: 'evocation',
        fromX: 2, fromY: 3, toX: 5, toY: 1, radiusFt: 10, damageType: 'lightning',
      });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 12px; align-items: center;">
        <button style="background: #0284c7; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;" @click=${castLightning}>
          ⚡ Cast Lightning Arc (Valeros -> Goblin Scout)
        </button>
        <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} watcherStatus="Arcane lightning arcs across grid coordinates with sharp ionizing sparks."></runefoble-board>
      </div>
    `;
  },
};

export const AbjurationShieldBarrierVFX: Story = {
  render: () => {
    const castShield = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      board?.triggerSpellVFX({ spellName: 'Shield', spellArchetype: 'abjuration', toX: 2, toY: 3 });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 12px; align-items: center;">
        <button style="background: #2563eb; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;" @click=${castShield}>
          🛡️ Cast Shield Reaction (Valeros)
        </button>
        <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} watcherStatus="Valeros invokes 'Shield'! A translucent hexagonal runic ward deflects the incoming attack."></runefoble-board>
      </div>
    `;
  },
};

export const RadialActionMenuBlooming: Story = {
  render: () => html`
    <runefoble-board id="radial-board" .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain}
      watcherStatus="Click on Valeros at (2,3) to bloom the contextual Bauhaus radial action menu."></runefoble-board>
  `,
};

export const RotatableConeSpellTemplate: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain} .activeAoE=${sampleAoETemplates.cone}
      watcherStatus="Drag the rotation handle to sweep the 15ft Burning Hands cone and target hostile monsters."></runefoble-board>
  `,
};

export const RotatableSphereSpellTemplate: Story = {
  render: () => html`
    <runefoble-board .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain} .activeAoE=${sampleAoETemplates.sphere}
      watcherStatus="20ft Fireball sphere centered over goblin ranks with live target halos."></runefoble-board>
  `,
};
