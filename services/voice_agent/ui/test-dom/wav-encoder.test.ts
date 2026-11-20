/**
 * WAV encoding of a Push to Talk utterance (TASK-0946).
 * The bytes must be a WAV that voice_agent `parse_audio_data` reads: PCM, mono, 16 bits, 16 kHz.
 */

import { describe, expect, it } from 'vitest';
import { bytesToBase64, encodeWav, floatToPcm16, UTTERANCE_SAMPLE_RATE } from '../src/wav-encoder.ts';

function tag(bytes: Uint8Array, offset: number): string {
  return String.fromCharCode(...bytes.subarray(offset, offset + 4));
}

describe('encodeWav', () => {
  const samples = new Float32Array([0, 0.5, -0.5, 1, -1, 2, -2]);
  const wav = encodeWav(samples, UTTERANCE_SAMPLE_RATE);
  const view = new DataView(wav.buffer, wav.byteOffset, wav.byteLength);

  it('writes a 44-byte RIFF header with two bytes for each sample', () => {
    expect(wav.length).toBe(44 + samples.length * 2);
    expect(tag(wav, 0)).toBe('RIFF');
    expect(view.getUint32(4, true)).toBe(36 + samples.length * 2);
    expect(tag(wav, 8)).toBe('WAVE');
    expect(tag(wav, 12)).toBe('fmt ');
    expect(tag(wav, 36)).toBe('data');
    expect(view.getUint32(40, true)).toBe(samples.length * 2);
  });

  it('declares PCM, mono, 16 bits a sample at 16 kHz', () => {
    expect(view.getUint32(16, true)).toBe(16);
    expect(view.getUint16(20, true)).toBe(1);
    expect(view.getUint16(22, true)).toBe(1);
    expect(view.getUint32(24, true)).toBe(16000);
    expect(view.getUint32(28, true)).toBe(32000);
    expect(view.getUint16(32, true)).toBe(2);
    expect(view.getUint16(34, true)).toBe(16);
  });

  it('scales samples to signed 16-bit integers and clips values outside [-1, 1]', () => {
    const pcm = Array.from({ length: samples.length }, (_, i) => view.getInt16(44 + i * 2, true));
    expect(pcm).toEqual([0, 16384, -16384, 32767, -32768, 32767, -32768]);
  });

  it('encodes an empty capture as a header with an empty data chunk', () => {
    const empty = encodeWav(new Float32Array(0), UTTERANCE_SAMPLE_RATE);
    expect(empty.length).toBe(44);
  });

  it('refuses a sample rate that is not a whole number above 0', () => {
    expect(() => encodeWav(samples, 0)).toThrow(RangeError);
    expect(() => encodeWav(samples, 16000.5)).toThrow(RangeError);
  });
});

describe('floatToPcm16', () => {
  it('maps the ends of the float range to the ends of the integer range', () => {
    expect(floatToPcm16(1)).toBe(32767);
    expect(floatToPcm16(-1)).toBe(-32768);
    expect(floatToPcm16(0)).toBe(0);
  });
});

describe('bytesToBase64', () => {
  it('gives the standard base64 text of the bytes', () => {
    expect(bytesToBase64(new TextEncoder().encode('RIFF'))).toBe('UklGRg==');
  });

  it('encodes more bytes than one conversion chunk', () => {
    const bytes = new Uint8Array(0x8000 * 2 + 3).fill(0xff);
    const decoded = Uint8Array.from(atob(bytesToBase64(bytes)), (c) => c.charCodeAt(0));
    expect(decoded).toEqual(bytes);
  });
});
