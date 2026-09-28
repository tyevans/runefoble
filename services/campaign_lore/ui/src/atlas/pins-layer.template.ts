import { html, type TemplateResult } from 'lit';
import type { AtlasPin } from './types.ts';

export interface PinsLayerProps {
  pins: AtlasPin[];
  activeLayer: string;
  activeEra?: string;
  selectedPinId?: string;
  onPinClick: (pin: AtlasPin, e: Event) => void;
}

export function filterVisiblePins(
  pins: AtlasPin[],
  activeLayer: string,
  activeEra?: string
): AtlasPin[] {
  return pins.filter((pin) => {
    if (activeEra && pin.era && !pin.era.toLowerCase().includes(activeEra.toLowerCase())) {
      return false;
    }
    return pin.layer === activeLayer || pin.layer === 'continental';
  });
}

export function calculateCanvasCoordinates(
  e: MouseEvent,
  panX: number,
  panY: number,
  zoomLevel: number
): { x: number; y: number } {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const rawX = (e.clientX - rect.left - panX) / zoomLevel;
  const rawY = (e.clientY - rect.top - panY) / zoomLevel;
  return { x: Math.round(rawX), y: Math.round(rawY) };
}

export function renderPinsLayer(props: PinsLayerProps): TemplateResult {
  const visiblePins = filterVisiblePins(props.pins, props.activeLayer, props.activeEra);

  return html`
    <g class="pins-layer">
      ${visiblePins.map((pin) => {
        const isSelected = props.selectedPinId === pin.pin_id;
        return html`
          <g
            class="pin-marker"
            data-pin-id=${pin.pin_id}
            transform="translate(${pin.coordinates.x}, ${pin.coordinates.y})"
            @click=${(e: Event) => props.onPinClick(pin, e)}
          >
            <circle
              r=${isSelected ? 10 : 7}
              class="pin-dot"
              style="fill: ${isSelected ? '#ffb703' : '#e63946'};"
            />
            <text x="12" y="4" class="pin-label">${pin.title}</text>
          </g>
        `;
      })}
    </g>
  `;
}
