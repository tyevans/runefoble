/**
 * WebAudio DSP Pipeline for Audio Capture & Dynamic Vocal Conditioning (TASK-0033).
 */

export class WebAudioPipeline {
  private audioContext: AudioContext | null = null;
  private localStream: MediaStream | null = null;
  private localSourceNode: MediaStreamAudioSourceNode | null = null;
  private analyserNode: AnalyserNode | null = null;
  private dspFilterNodes: AudioNode[] = [];
  private outputGainNode: GainNode | null = null;

  private isMuted: boolean = false;
  private activeFilters: string[] = [];

  public async startMicrophone(): Promise<MediaStream> {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('navigator.mediaDevices.getUserMedia not available in this environment');
    }

    this.localStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioCtxClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioCtxClass) {
      this.audioContext = new AudioCtxClass();
      this.localSourceNode = this.audioContext.createMediaStreamSource(this.localStream);
      this.analyserNode = this.audioContext.createAnalyser();
      this.analyserNode.fftSize = 256;
      this.outputGainNode = this.audioContext.createGain();

      this.rebuildDspGraph();
    }

    return this.localStream;
  }

  public applyDspFilters(filters: string[]): void {
    this.activeFilters = [...filters];
    this.rebuildDspGraph();
  }

  public rebuildDspGraph(): void {
    if (!this.audioContext || !this.localSourceNode || !this.analyserNode || !this.outputGainNode) {
      return;
    }

    try {
      this.localSourceNode.disconnect();
      for (const node of this.dspFilterNodes) {
        node.disconnect();
      }
      this.analyserNode.disconnect();
    } catch {
      // Ignored
    }

    this.dspFilterNodes = [];
    let currentNode: AudioNode = this.localSourceNode;

    for (const filter of this.activeFilters) {
      if (filter === 'underwater') {
        const lowpass = this.audioContext.createBiquadFilter();
        lowpass.type = 'lowpass';
        lowpass.frequency.setValueAtTime(450, this.audioContext.currentTime);
        currentNode.connect(lowpass);
        currentNode = lowpass;
        this.dspFilterNodes.push(lowpass);
      } else if (filter === 'whisper') {
        const highpass = this.audioContext.createBiquadFilter();
        highpass.type = 'highpass';
        highpass.frequency.setValueAtTime(800, this.audioContext.currentTime);
        currentNode.connect(highpass);
        currentNode = highpass;
        this.dspFilterNodes.push(highpass);
      } else if (filter === 'ethereal') {
        const delay = this.audioContext.createDelay(1.0);
        delay.delayTime.setValueAtTime(0.25, this.audioContext.currentTime);
        const feedback = this.audioContext.createGain();
        feedback.gain.setValueAtTime(0.4, this.audioContext.currentTime);

        currentNode.connect(delay);
        delay.connect(feedback);
        feedback.connect(delay);

        currentNode = delay;
        this.dspFilterNodes.push(delay, feedback);
      } else if (filter === 'drunk') {
        const bandpass = this.audioContext.createBiquadFilter();
        bandpass.type = 'bandpass';
        bandpass.frequency.setValueAtTime(1000, this.audioContext.currentTime);
        currentNode.connect(bandpass);
        currentNode = bandpass;
        this.dspFilterNodes.push(bandpass);
      }
    }

    currentNode.connect(this.analyserNode);
    this.analyserNode.connect(this.outputGainNode);
  }

  public setMute(isMuted: boolean): void {
    this.isMuted = isMuted;
    if (this.localStream) {
      for (const track of this.localStream.getAudioTracks()) {
        track.enabled = !isMuted;
      }
    }
  }

  public getAudioLevel(): { level: number; isSpeaking: boolean } {
    if (!this.analyserNode || this.isMuted) {
      return { level: 0.0, isSpeaking: false };
    }

    const dataArray = new Uint8Array(this.analyserNode.frequencyBinCount);
    this.analyserNode.getByteFrequencyData(dataArray);

    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i];
    }
    const level = Math.min(1.0, sum / (dataArray.length * 128));
    return {
      level: Number(level.toFixed(2)),
      isSpeaking: level > 0.15,
    };
  }

  public getLocalStream(): MediaStream | null {
    return this.localStream;
  }

  public close(): void {
    if (this.localStream) {
      for (const track of this.localStream.getTracks()) {
        track.stop();
      }
      this.localStream = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}
