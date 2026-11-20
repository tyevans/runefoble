/**
 * PCM 16-bit WAV encoding for Push to Talk utterances (TASK-0946).
 *
 * Pure functions. No browser audio API is used here, so the encoding has one tested definition.
 * voice_agent reads the result with `parse_audio_data` (`services/voice_agent/src/voice_agent/vad.py`).
 */

/** The sample rate that Push to Talk sends. The speech engines take 16 kHz mono. */
export const UTTERANCE_SAMPLE_RATE = 16000;

const WAV_HEADER_BYTES = 44;
const BYTES_PER_SAMPLE = 2;

/** Converts one float sample in [-1, 1] to a signed 16-bit integer. Values outside are clipped. */
export function floatToPcm16(sample: number): number {
  const clipped = Math.max(-1, Math.min(1, sample));
  return clipped < 0 ? Math.round(clipped * 0x8000) : Math.round(clipped * 0x7fff);
}

/**
 * Encodes mono float samples as a RIFF WAV file: PCM format 1, one channel, 16 bits a sample,
 * little endian. The header is 44 bytes. The data chunk holds two bytes for each sample.
 */
export function encodeWav(samples: Float32Array, sampleRate: number): Uint8Array {
  if (!Number.isInteger(sampleRate) || sampleRate <= 0) {
    throw new RangeError(`The sample rate must be a whole number above 0, not ${sampleRate}.`);
  }
  const dataBytes = samples.length * BYTES_PER_SAMPLE;
  const buffer = new ArrayBuffer(WAV_HEADER_BYTES + dataBytes);
  const view = new DataView(buffer);
  const writeTag = (offset: number, tag: string) => {
    for (let i = 0; i < tag.length; i++) view.setUint8(offset + i, tag.charCodeAt(i));
  };
  writeTag(0, 'RIFF');
  view.setUint32(4, 36 + dataBytes, true);
  writeTag(8, 'WAVE');
  writeTag(12, 'fmt ');
  view.setUint32(16, 16, true); // fmt chunk size for PCM
  view.setUint16(20, 1, true); // audio format: PCM
  view.setUint16(22, 1, true); // channels: mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * BYTES_PER_SAMPLE, true); // byte rate
  view.setUint16(32, BYTES_PER_SAMPLE, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeTag(36, 'data');
  view.setUint32(40, dataBytes, true);
  for (let i = 0; i < samples.length; i++) {
    view.setInt16(WAV_HEADER_BYTES + i * BYTES_PER_SAMPLE, floatToPcm16(samples[i]), true);
  }
  return new Uint8Array(buffer);
}

/** Returns the standard base64 text of `bytes`, as `audio_base64` takes it. */
export function bytesToBase64(bytes: Uint8Array): string {
  const chunk = 0x8000;
  let binary = '';
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}
