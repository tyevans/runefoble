export interface WaveformDrawOptions {
  canvas: HTMLCanvasElement;
  isListening: boolean;
  analyser: AnalyserNode | null;
  activeFilters: string[];
  simPhase: number;
}

export interface WaveformMetrics {
  level: number;
  peak: number;
  nextSimPhase: number;
}

function getComputedColor(element: Element, varName: string, fallback: string): string {
  try {
    if (typeof window !== 'undefined' && window.getComputedStyle) {
      const val = window.getComputedStyle(element).getPropertyValue(varName).trim();
      if (val) return val;
    }
  } catch {
    // fallback
  }
  return fallback;
}

/**
 * Render real-time audio waveform or idle baseline onto HTML5 canvas with Bauhaus styling.
 */
export function renderAudioWaveform(options: WaveformDrawOptions): WaveformMetrics {
  const { canvas, isListening, analyser, activeFilters, simPhase } = options;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return { level: 0, peak: 0, nextSimPhase: simPhase };
  }

  const width = canvas.width;
  const height = canvas.height;

  // Clear background with theme-adaptive canvas/inset color
  const bgColor = getComputedColor(canvas, '--rf-bg-inset', 'transparent');
  if (bgColor && bgColor !== 'transparent') {
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);
  } else {
    ctx.clearRect(0, 0, width, height);
  }

  // Center division axis
  ctx.strokeStyle = getComputedColor(canvas, '--rf-border-subtle', 'rgba(128, 128, 128, 0.25)');
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height / 2);
  ctx.lineTo(width, height / 2);
  ctx.stroke();

  if (!isListening) {
    // Muted idle dashed baseline
    ctx.strokeStyle = getComputedColor(canvas, '--rf-text-muted', 'rgba(128, 128, 128, 0.5)');
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
    ctx.setLineDash([]);
    return { level: 0, peak: 0, nextSimPhase: simPhase };
  }

  let level = 0;
  let peak = 0;
  const points: number[] = [];
  const sampleCount = 64;
  let nextPhase = simPhase;

  if (analyser) {
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < sampleCount; i++) {
      const idx = Math.floor((i / sampleCount) * data.length);
      const val = (data[idx] - 128) / 128;
      points.push(val);
      sum += val * val;
      peak = Math.max(peak, Math.abs(val));
    }
    level = Math.min(1, Math.sqrt(sum / sampleCount) * 2);
  } else {
    // Simulated reactive audio synthesis
    nextPhase += 0.12;
    const isDrunk = activeFilters.includes('drunk');
    const isWhisper = activeFilters.includes('whisper');
    const wobble = isDrunk ? Math.sin(nextPhase * 0.5) * 0.35 : 0;
    const amp = isWhisper ? 0.3 : 0.75;

    for (let i = 0; i < sampleCount; i++) {
      const t = (i / sampleCount) * Math.PI * 4;
      const val =
        (Math.sin(t + nextPhase) * 0.6 +
          Math.sin(t * 2.3 - nextPhase) * 0.3 +
          wobble) *
        amp;
      points.push(val);
      peak = Math.max(peak, Math.abs(val));
    }
    level = 0.55 + Math.sin(nextPhase * 0.8) * 0.25;
  }

  // Active waveform stroke
  const strokeColor = activeFilters.includes('drunk')
    ? getComputedColor(canvas, '--rf-accent-tertiary', 'orange')
    : getComputedColor(canvas, '--rf-accent-primary', 'red');

  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2;
  ctx.beginPath();

  for (let i = 0; i < points.length; i++) {
    const x = (i / (points.length - 1)) * width;
    const y = height / 2 + points[i] * (height / 2.4);
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  return {
    level: Math.round(level * 100) / 100,
    peak: Math.round(peak * 100) / 100,
    nextSimPhase: nextPhase,
  };
}
