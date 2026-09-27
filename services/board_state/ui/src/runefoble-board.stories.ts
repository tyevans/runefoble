import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-board.ts';
import type { BoardToken, GhostPreviewState, TerrainCell } from './runefoble-board.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleBoard',
  component: 'runefoble-board',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleTokens: BoardToken[] = [
  { id: '1', name: 'Valeros', x: 2, y: 3, color: '#2563eb', hp: 38, maxHp: 45, visionRadius: 2 },
  { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: '#db2777', hp: 28, maxHp: 32, visionRadius: 2 },
  { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: '#16a34a', hp: 7, maxHp: 12 },
  { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: '#dc2626', hp: 52, maxHp: 75 },
];

const sampleTerrain: TerrainCell[] = [
  { x: 3, y: 2, terrainType: 'difficult' },
  { x: 4, y: 2, terrainType: 'difficult' },
  { x: 4, y: 3, terrainType: 'difficult' },
  { x: 5, y: 4, terrainType: 'normal', hazard: 'lava' },
];

export const Default: Story = {
  render: () => html`
    <runefoble-board
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      watcherStatus="Tracking 4 active tokens. Awaiting DM narration."
    ></runefoble-board>
  `,
};

// Story 1: Token kinematics with path measurement and terrain highlight
export const TokenKinematicsAndMeasurement: Story = {
  render: () => html`
    <runefoble-board
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      .terrainCells=${sampleTerrain}
      watcherStatus="Drag any token to test tactile kinematics, 5-ft waypoint ruler, and terrain penalties."
    ></runefoble-board>
  `,
};

// Story 2: Spoken ghost preview with interactive confirmation tap
export const SpokenGhostPreviewWithConfirmation: Story = {
  render: () => {
    const previewState: GhostPreviewState = {
      tokenId: '1',
      tokenName: 'Valeros',
      fromX: 2,
      fromY: 3,
      toX: 5,
      toY: 3,
      totalDistanceFt: 20, // 2 normal (10ft) + 1 difficult (10ft) = 20ft
      baseDistanceFt: 15,
      terrainPenaltyFt: 5,
      movementCost: 4,
      waypoints: [
        { x: 3, y: 3, step: 1, distanceFt: 5, isDifficult: false },
        { x: 4, y: 3, step: 2, distanceFt: 15, isDifficult: true },
        { x: 5, y: 3, step: 3, distanceFt: 20, isDifficult: false },
      ],
      difficultCells: [[4, 3]],
      hazardCells: [],
      timeoutSeconds: 15,
      remainingSeconds: 14,
      speakerName: 'Valeros',
      rawTranscript: 'Valeros charges 3 squares east toward the goblin flank',
    };

    return html`
      <runefoble-board
        .cols=${8}
        .rows=${8}
        .tokens=${sampleTokens}
        .terrainCells=${sampleTerrain}
        .activeGhost=${previewState}
        watcherStatus="Speech Intent Parsed: 'Valeros charges 3 squares east'. Click ghost or Confirm to execute."
      ></runefoble-board>
    `;
  },
};

// Story 3: Ghost cancellation and timeout rollback
export const GhostCancellationAndTimeout: Story = {
  render: () => {
    const expiringGhost: GhostPreviewState = {
      tokenId: '2',
      tokenName: 'Kyra (AI)',
      fromX: 3,
      fromY: 3,
      toX: 5,
      toY: 4,
      totalDistanceFt: 15,
      waypoints: [
        { x: 4, y: 3, step: 1, distanceFt: 10, isDifficult: true },
        { x: 5, y: 4, step: 2, distanceFt: 15, isDifficult: false, hazard: 'lava' },
      ],
      difficultCells: [[4, 3]],
      hazardCells: [[5, 4]],
      hazardTriggered: 'lava',
      damageDice: '2d10',
      timeoutSeconds: 15,
      remainingSeconds: 4,
      speakerName: 'Kyra',
      rawTranscript: 'Kyra moves toward the molten altar',
    };

    return html`
      <runefoble-board
        .cols=${8}
        .rows=${8}
        .tokens=${sampleTokens}
        .terrainCells=${sampleTerrain}
        .activeGhost=${expiringGhost}
        watcherStatus="Ghost preview expiring in 4s. Tap Cancel to rollback or let timeout discard."
      ></runefoble-board>
    `;
  },
};

export const ActiveEncounter: Story = {
  render: () => html`
    <runefoble-board
      .cols=${10}
      .rows=${8}
      .tokens=${[
        ...sampleTokens,
        { id: '5', name: 'Ezren', x: 1, y: 4, color: '#9333ea', hp: 22, maxHp: 22, visionRadius: 3 },
      ]}
      .terrainCells=${sampleTerrain}
      watcherStatus="Voice detected: 'Valeros charges 2 squares east!'"
    ></runefoble-board>
  `,
};

export const FogOfWarEncounter: Story = {
  render: () => html`
    <runefoble-board
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      .fogOfWar=${true}
      watcherStatus="Fog of War shrouds unrevealed dungeon corridors."
    ></runefoble-board>
  `,
};

export const ActiveTurn: Story = {
  render: () => html`
    <runefoble-board
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      activeTurnTokenId="1"
      watcherStatus="Active turn: Valeros (Fighter). 30 ft movement remaining."
    ></runefoble-board>
  `,
};

export const MultiplayerTokens: Story = {
  render: () => html`
    <runefoble-board
      .cols=${10}
      .rows=${10}
      .fogOfWar=${true}
      activeTurnTokenId="2"
      .tokens=${[
        { id: '1', name: 'Valeros', x: 3, y: 4, color: '#2563eb', hp: 42, maxHp: 45, visionRadius: 2 },
        { id: '2', name: 'Kyra (AI)', x: 4, y: 4, isAiControlled: true, color: '#db2777', hp: 12, maxHp: 32, visionRadius: 3 },
        { id: '3', name: 'Merisiel', x: 2, y: 5, color: '#059669', hp: 26, maxHp: 28, visionRadius: 3 },
        { id: '4', name: 'Ezren', x: 4, y: 5, color: '#7c3aed', hp: 18, maxHp: 20, visionRadius: 2 },
        { id: '5', name: 'Skeleton Archer', x: 8, y: 1, isHostile: true, color: '#dc2626', hp: 11, maxHp: 11 },
        { id: '6', name: 'Necromancer', x: 8, y: 8, isHostile: true, color: '#991b1b', hp: 35, maxHp: 40 },
      ]}
      watcherStatus="Turn 4: Kyra (AI Stand-in) is deliberating tactical healing spell."
    ></runefoble-board>
  `,
};

// Story 7: Evocation Firestorm with interactive spellcast button
export const EvocationFirestormVFX: Story = {
  render: () => {
    const castFireball = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      if (board) {
        board.triggerSpellVFX({
          spellName: 'Fireball',
          spellArchetype: 'evocation',
          fromX: 2,
          fromY: 3,
          toX: 6,
          toY: 5,
          radiusFt: 20,
          damageType: 'fire',
        });
      }
    };

    const advanceRounds = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      if (board?.particleEngine) {
        board.particleEngine.decayDecals(1);
        board.requestUpdate();
      }
    };

    return html`
      <div style="display: flex; flex-direction: column; gap: 12px; align-items: center;">
        <div style="display: flex; gap: 8px;">
          <button
            style="background: #dc2626; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;"
            @click=${castFireball}
          >
            🔥 Cast Fireball (Valeros -> Red Dragon)
          </button>
          <button
            style="background: #4b5563; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;"
            @click=${advanceRounds}
          >
            ⏳ Advance Round (Decay Scorched Decals)
          </button>
        </div>
        <runefoble-board
          .cols=${8}
          .rows=${8}
          .tokens=${sampleTokens}
          watcherStatus="Nadia: 'I cast Fireball centered on the Red Dragon at (6, 5)!'"
        ></runefoble-board>
      </div>
    `;
  },
};

// Story 8: Evocation Lightning Arc with interactive chain trigger
export const EvocationLightningArcVFX: Story = {
  render: () => {
    const castLightning = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      if (board) {
        board.triggerSpellVFX({
          spellName: 'Lightning Bolt',
          spellArchetype: 'evocation',
          fromX: 2,
          fromY: 3,
          toX: 5,
          toY: 1,
          radiusFt: 10,
          damageType: 'lightning',
        });
      }
    };

    return html`
      <div style="display: flex; flex-direction: column; gap: 12px; align-items: center;">
        <button
          style="background: #0284c7; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;"
          @click=${castLightning}
        >
          ⚡ Cast Lightning Arc (Valeros -> Goblin Scout)
        </button>
        <runefoble-board
          .cols=${8}
          .rows=${8}
          .tokens=${sampleTokens}
          watcherStatus="Arcane lightning arcs across grid coordinates with sharp ionizing sparks."
        ></runefoble-board>
      </div>
    `;
  },
};

// Story 9: Abjuration Hexagonal Arcane Shield Barrier
export const AbjurationShieldBarrierVFX: Story = {
  render: () => {
    const castShield = (e: Event) => {
      const board = (e.target as HTMLElement).parentElement?.querySelector('runefoble-board') as any;
      if (board) {
        board.triggerSpellVFX({
          spellName: 'Shield',
          spellArchetype: 'abjuration',
          toX: 2,
          toY: 3,
        });
      }
    };

    return html`
      <div style="display: flex; flex-direction: column; gap: 12px; align-items: center;">
        <button
          style="background: #2563eb; color: white; border: none; padding: 8px 16px; font-weight: 700; border-radius: 4px; cursor: pointer;"
          @click=${castShield}
        >
          🛡️ Cast Shield Reaction (Valeros)
        </button>
        <runefoble-board
          .cols=${8}
          .rows=${8}
          .tokens=${sampleTokens}
          watcherStatus="Valeros invokes 'Shield'! A translucent hexagonal runic ward deflects the incoming attack."
        ></runefoble-board>
      </div>
    `;
  },
};

// Story 10: Contextual radial action menu blooming
export const RadialActionMenuBlooming: Story = {
  render: () => {
    return html`
      <runefoble-board
        id="radial-board"
        .cols=${8}
        .rows=${8}
        .tokens=${sampleTokens}
        .terrainCells=${sampleTerrain}
        watcherStatus="Click on Valeros at (2,3) to bloom the contextual Bauhaus radial action menu."
      ></runefoble-board>
    `;
  },
};

// Story 11: Rotatable 15-foot Burning Hands cone with live token targeting halo
export const RotatableConeSpellTemplate: Story = {
  render: () => {
    return html`
      <runefoble-board
        .cols=${8}
        .rows=${8}
        .tokens=${sampleTokens}
        .terrainCells=${sampleTerrain}
        .activeAoE=${{
          shape: 'cone',
          originX: 2.5,
          originY: 3.5,
          directionDeg: 45,
          radiusFt: 15,
          spellName: 'Burning Hands (15-foot Cone)',
          casterTokenId: '1',
        }}
        watcherStatus="Drag the rotation handle to sweep the 15ft Burning Hands cone and target hostile monsters."
      ></runefoble-board>
    `;
  },
};

// Story 12: Rotatable 20-foot Sphere (Fireball) with target intersection halos
export const RotatableSphereSpellTemplate: Story = {
  render: () => {
    return html`
      <runefoble-board
        .cols=${8}
        .rows=${8}
        .tokens=${sampleTokens}
        .terrainCells=${sampleTerrain}
        .activeAoE=${{
          shape: 'sphere',
          originX: 5.5,
          originY: 2.5,
          directionDeg: 0,
          radiusFt: 20,
          spellName: 'Fireball (20-foot Radius)',
        }}
        watcherStatus="20ft Fireball sphere centered over goblin ranks with live target halos."
      ></runefoble-board>
    `;
  },
};

