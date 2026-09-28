import type { CampaignHeatmapResponse, HeatmapCell, HazardHotspot, KnockoutLocation, MovementCorridor } from '../types.ts';

export type MetricType = 'all' | 'damage' | 'hit' | 'movement';

export interface HeatmapDrawOptions {
  canvas: HTMLCanvasElement;
  gridSize: number;
  cellPixelSize: number;
  selectedMetric: MetricType;
  heatmapData: CampaignHeatmapResponse | null;
  selectedCell: HeatmapCell | null;
}

export function getCellColor(val: number, max: number): string {
  if (val <= 0 || max <= 0) return 'rgba(0, 0, 0, 0)';
  const ratio = Math.min(val / max, 1);
  if (ratio < 0.25) return `rgba(42, 157, 143, ${0.3 + ratio * 0.4})`;
  if (ratio < 0.5) return `rgba(233, 196, 106, ${0.4 + ratio * 0.5})`;
  if (ratio < 0.75) return `rgba(244, 162, 97, ${0.5 + ratio * 0.4})`;
  return `rgba(230, 57, 70, ${0.6 + ratio * 0.4})`;
}

export function drawGridLines(ctx: CanvasRenderingContext2D, w: number, h: number, size: number): void {
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 1;
  for (let x = 0; x <= w; x += size) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let y = 0; y <= h; y += size) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }
}

export function drawDensityCells(ctx: CanvasRenderingContext2D, cells: HeatmapCell[] | undefined, metric: MetricType, size: number): void {
  if (!cells?.length) return;
  const getVal = (c: HeatmapCell) =>
    metric === 'damage' ? c.damage_total : metric === 'hit' ? c.hit_count : metric === 'movement' ? c.movement_count : c.density || 1;
  const maxVal = Math.max(...cells.map(getVal), 1);
  for (const cell of cells) {
    const val = getVal(cell);
    if (val > 0) {
      ctx.fillStyle = getCellColor(val, maxVal);
      ctx.fillRect(cell.x * size + 1, cell.y * size + 1, size - 2, size - 2);
    }
  }
}

export function drawCorridors(ctx: CanvasRenderingContext2D, corridors: MovementCorridor[] | undefined, size: number): void {
  if (!corridors?.length) return;
  ctx.strokeStyle = '#2a9d8f';
  ctx.lineWidth = 2.5;
  ctx.setLineDash([4, 4]);
  for (const c of corridors) {
    const sx = c.fromX * size + size / 2, sy = c.fromY * size + size / 2;
    const ex = c.toX * size + size / 2, ey = c.toY * size + size / 2;
    ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
    ctx.fillStyle = '#2a9d8f';
    ctx.beginPath(); ctx.arc(ex, ey, 3, 0, Math.PI * 2); ctx.fill();
  }
  ctx.setLineDash([]);
}

export function drawHazards(ctx: CanvasRenderingContext2D, hazards: HazardHotspot[] | undefined, size: number): void {
  for (const h of hazards || []) {
    const px = h.x * size, py = h.y * size;
    ctx.fillStyle = 'rgba(231, 111, 81, 0.35)';
    ctx.fillRect(px + 2, py + 2, size - 4, size - 4);
    ctx.strokeStyle = '#e76f51';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(px + 2, py + 2, size - 4, size - 4);
    ctx.fillStyle = '#e76f51';
    ctx.font = 'bold 10px monospace';
    ctx.fillText('⚠', px + 4, py + 12);
  }
}

export function drawKnockouts(ctx: CanvasRenderingContext2D, knockouts: KnockoutLocation[] | undefined, size: number): void {
  for (const k of knockouts || []) {
    ctx.fillStyle = '#121212';
    ctx.font = '14px sans-serif';
    ctx.fillText('💀', k.x * size + size / 4, k.y * size + (size * 3) / 4);
  }
}

export function drawSelection(ctx: CanvasRenderingContext2D, sel: HeatmapCell | null, size: number): void {
  if (!sel) return;
  ctx.strokeStyle = '#121212';
  ctx.lineWidth = 3;
  ctx.strokeRect(sel.x * size, sel.y * size, size, size);
}

export function renderHeatmapCanvas(options: HeatmapDrawOptions): void {
  const { canvas, gridSize, cellPixelSize, selectedMetric, heatmapData, selectedCell } = options;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const width = gridSize * cellPixelSize, height = gridSize * cellPixelSize;
  canvas.width = width; canvas.height = height;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  drawGridLines(ctx, width, height, cellPixelSize);
  drawDensityCells(ctx, heatmapData?.cells, selectedMetric, cellPixelSize);
  drawCorridors(ctx, heatmapData?.corridors, cellPixelSize);
  drawHazards(ctx, heatmapData?.hazards, cellPixelSize);
  drawKnockouts(ctx, heatmapData?.knockouts, cellPixelSize);
  drawSelection(ctx, selectedCell, cellPixelSize);
}
