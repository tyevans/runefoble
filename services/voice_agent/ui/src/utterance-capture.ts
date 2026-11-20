/**
 * Microphone capture for one Push to Talk utterance (TASK-0946).
 *
 * `UtteranceCapture.open` asks for the microphone, connects it to an analyser for the level
 * meter, and starts a `MediaRecorder` on the same stream. `stop` ends the recording, releases
 * the microphone, and returns the recorded blob. `blobToWavBase64` decodes the blob, resamples it
 * to 16 kHz mono with an `OfflineAudioContext`, and encodes it as PCM 16-bit WAV.
 * Every failure rejects. Nothing returns substitute audio.
 */

import { bytesToBase64, encodeWav, UTTERANCE_SAMPLE_RATE } from './wav-encoder.ts';

export class UtteranceCapture {
  private readonly chunks: Blob[] = [];
  private readonly stream: MediaStream;
  private readonly audioCtx: AudioContext;
  private readonly recorder: MediaRecorder;
  readonly analyser: AnalyserNode;

  private constructor(stream: MediaStream, audioCtx: AudioContext, recorder: MediaRecorder, analyser: AnalyserNode) {
    this.stream = stream;
    this.audioCtx = audioCtx;
    this.recorder = recorder;
    this.analyser = analyser;
    recorder.addEventListener('dataavailable', (e) => {
      if (e.data.size > 0) this.chunks.push(e.data);
    });
  }

  /** Opens the microphone and starts recording. Rejects when the browser refuses the microphone. */
  static async open(): Promise<UtteranceCapture> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('This browser gives no microphone access.');
    }
    if (typeof MediaRecorder === 'undefined') {
      throw new Error('This browser cannot record audio.');
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioCtx = new AudioContext();
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    audioCtx.createMediaStreamSource(stream).connect(analyser);
    const recorder = new MediaRecorder(stream);
    const capture = new UtteranceCapture(stream, audioCtx, recorder, analyser);
    recorder.start();
    return capture;
  }

  /** Stops the recording, releases the microphone, and returns the recorded audio. */
  async stop(): Promise<Blob> {
    const stopped = new Promise<void>((resolve) => {
      this.recorder.addEventListener('stop', () => resolve(), { once: true });
    });
    if (this.recorder.state !== 'inactive') this.recorder.stop();
    await stopped;
    this.release();
    return new Blob(this.chunks, { type: this.recorder.mimeType });
  }

  /** Releases the microphone and the audio context without a result. */
  cancel(): void {
    if (this.recorder.state !== 'inactive') this.recorder.stop();
    this.release();
  }

  private release(): void {
    this.stream.getTracks().forEach((track) => track.stop());
    if (this.audioCtx.state !== 'closed') void this.audioCtx.close();
  }
}

/** Downmixes a decoded buffer to 16 kHz mono float samples. */
async function resampleToUtteranceRate(decoded: AudioBuffer): Promise<Float32Array> {
  const frames = Math.ceil(decoded.duration * UTTERANCE_SAMPLE_RATE);
  if (frames === 0) return new Float32Array(0);
  const offline = new OfflineAudioContext(1, frames, UTTERANCE_SAMPLE_RATE);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const rendered = await offline.startRendering();
  return rendered.getChannelData(0);
}

/**
 * Converts a recorded blob into the base64 WAV that `POST /api/v1/voice/transcribe` takes.
 * Rejects when the blob holds no audio or the browser cannot decode it.
 */
export async function blobToWavBase64(blob: Blob): Promise<string> {
  if (blob.size === 0) throw new Error('No audio was recorded. Hold the button while you speak.');
  const ctx = new AudioContext();
  try {
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
    const samples = await resampleToUtteranceRate(decoded);
    if (samples.length === 0) throw new Error('No audio was recorded. Hold the button while you speak.');
    return bytesToBase64(encodeWav(samples, UTTERANCE_SAMPLE_RATE));
  } finally {
    void ctx.close();
  }
}
