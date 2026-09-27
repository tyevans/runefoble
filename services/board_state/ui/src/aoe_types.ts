import type { SVGTemplateResult } from 'lit';
import type { AoEShape, AoETemplateConfig, BoardToken } from './board-types.ts';

export type { AoEShape, AoETemplateConfig, BoardToken };

export interface Point2D {
  x: number;
  y: number;
}

export interface AoEHandleEvents {
  onOriginDown: (e: PointerEvent) => void;
  onOriginMove: (e: PointerEvent) => void;
  onOriginUp: (e: PointerEvent) => void;
  onRotationDown: (e: PointerEvent) => void;
  onRotationMove: (e: PointerEvent) => void;
  onRotationUp: (e: PointerEvent) => void;
}

export interface AoERenderPaths {
  shapeSvg: SVGTemplateResult;
  rotHandleX: number;
  rotHandleY: number;
}

export interface AoEChangeDetail {
  config: AoETemplateConfig;
  affectedTokenIds: string[];
  affectedCells: [number, number][];
}

export const AOE_COLOR_TOKENS = {
  coneFill: 'rgba(230, 57, 70, 0.28)',
  coneStroke: 'var(--rf-accent-primary, #e63946)',
  sphereFill: 'rgba(255, 183, 3, 0.25)',
  sphereStroke: 'var(--rf-accent-tertiary, #ffb703)',
  lineFill: 'rgba(69, 123, 157, 0.28)',
  lineStroke: 'var(--rf-accent-secondary, #1d3557)',
  cubeFill: 'rgba(42, 157, 143, 0.28)',
  cubeStroke: 'var(--rf-accent-primary, #2a9d8f)',
} as const;
