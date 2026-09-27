/**
 * WebAudio acoustic synthesis and foley tray clatter engine (TASK-0170).
 * Generates tactile polyhedral dice clatters, perimeter wall bounces, and settle chimes.
 */

export type ImpactType = 'wall' | 'floor' | 'token' | 'dice';

export interface AudioImpactOptions {
  velocity?: number;
  impactType?: ImpactType;
  muted?: boolean;
}

export class DiceTrayAudio {
  private ctx: AudioContext | null = null;
  public muted = false;
  public volume = 0.8;
  public onImpact?: (type: ImpactType, velocity: number) => void;

  private getContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return null;
    if (!this.ctx || this.ctx.state === 'closed') {
      try {
        this.ctx = new AudioCtx();
      } catch {
        return null;
      }
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  public playImpact(options?: AudioImpactOptions): void {
    if (this.muted || options?.muted) return;
    const vel = options?.velocity ?? 3.0;
    const type = options?.impactType ?? 'floor';
    this.onImpact?.(type, vel);

    const ctx = this.getContext();
    if (!ctx) return;

    try {
      const normVel = Math.min(1.0, Math.max(0.1, vel / 6.0));
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();

      const profile = {
        wall: { startFreq: 180, endFreq: 60, decay: 0.12, filterFreq: 400, type: 'triangle' as OscillatorType },
        floor: { startFreq: 420, endFreq: 110, decay: 0.08, filterFreq: 1200, type: 'sine' as OscillatorType },
        token: { startFreq: 750, endFreq: 260, decay: 0.10, filterFreq: 2500, type: 'square' as OscillatorType },
        dice: { startFreq: 880, endFreq: 320, decay: 0.09, filterFreq: 3000, type: 'sine' as OscillatorType },
      }[type];

      osc.type = profile.type;
      osc.frequency.setValueAtTime(profile.startFreq, now);
      osc.frequency.exponentialRampToValueAtTime(profile.endFreq, now + profile.decay);

      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(profile.filterFreq, now);

      const targetGain = Math.max(0.01, this.volume * normVel * 0.45);
      gain.gain.setValueAtTime(targetGain, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + profile.decay);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + profile.decay);
    } catch {
      // Graceful fallback for restricted audio contexts
    }
  }

  public playSettle(faceValue: number, isCritical = false): void {
    if (this.muted) return;
    const ctx = this.getContext();
    if (!ctx) return;
    try {
      const isCrit = isCritical || faceValue === 20;
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = isCrit ? 'triangle' : 'sine';
      osc.frequency.setValueAtTime(isCrit ? 523.25 : 330, now);
      if (isCrit) {
        osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.15);
      }
      gain.gain.setValueAtTime(this.volume * 0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + (isCrit ? 0.35 : 0.18));
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + (isCrit ? 0.35 : 0.18));
    } catch {
      // Fallback
    }
  }

  public setMuted(muted: boolean): void {
    this.muted = muted;
  }

  public close(): void {
    try {
      this.ctx?.close();
    } catch {
      // Ignore
    }
    this.ctx = null;
  }
}
