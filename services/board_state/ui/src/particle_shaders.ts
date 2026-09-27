/**
 * WebGL Shaders for tactical particle magic and spell archetype VFX.
 * Incorporates ADR-0012 accessible dark and light mode bloom calibrations.
 */

import type { Particle } from './particle_types.ts';

export const PARTICLE_VERTEX_SHADER = `
precision mediump float;

attribute vec2 a_quad_pos;      // [-1, 1] quad coordinate
attribute vec2 a_particle_pos;  // Particle center in canvas pixels
attribute vec4 a_color;         // [r, g, b, a]
attribute float a_size;         // Particle pixel size
attribute float a_life;         // Remaining life [0..1]
attribute float a_type;         // 0=burst/radial, 1=lightning, 2=hex rune, 3=spiral vortex
attribute float a_rotation;     // Rotation angle in radians

uniform vec2 u_resolution;      // Canvas [width, height]

varying vec4 v_color;
varying vec2 v_local_pos;
varying float v_type;
varying float v_life;

void main() {
  v_color = a_color;
  v_local_pos = a_quad_pos;
  v_type = a_type;
  v_life = a_life;

  // Apply rotation to quad vertices
  float c = cos(a_rotation);
  float s = sin(a_rotation);
  vec2 rotated_quad = vec2(
    a_quad_pos.x * c - a_quad_pos.y * s,
    a_quad_pos.x * s + a_quad_pos.y * c
  );

  vec2 pixel_pos = a_particle_pos + rotated_quad * a_size;
  // Convert 2D pixel coordinates to OpenGL clip space [-1, 1]
  vec2 zero_to_one = pixel_pos / u_resolution;
  vec2 clip_space = vec2(zero_to_one.x * 2.0 - 1.0, 1.0 - zero_to_one.y * 2.0);

  gl_Position = vec4(clip_space, 0.0, 1.0);
}
`;

export const PARTICLE_FRAGMENT_SHADER = `
precision mediump float;

varying vec4 v_color;
varying vec2 v_local_pos;
varying float v_type;
varying float v_life;

uniform float u_bloom_intensity; // ADR-0012 dynamic bloom scaling
uniform int u_theme_mode;        // 0=dark, 1=light, 2=high-contrast

void main() {
  float dist = length(v_local_pos);
  if (dist > 1.0) {
    discard;
  }

  float alpha = 0.0;

  if (v_type > 1.5 && v_type < 2.5) {
    // Hexagonal rune / ward barrier edge (6-fold symmetry)
    float angle = atan(v_local_pos.y, v_local_pos.x);
    float hex = cos(mod(angle, 1.047197) - 0.523598);
    float r = dist * hex;
    alpha = smoothstep(0.95, 0.75, r) * v_color.a * v_life;
    if (dist < 0.7) {
      alpha *= 0.35; // Translucent shield interior
    }
  } else if (v_type > 2.5) {
    // Dimensional vortex swirl
    float angle = atan(v_local_pos.y, v_local_pos.x);
    float spiral = sin(angle * 3.0 + dist * 12.0);
    alpha = (1.0 - dist) * (0.4 + 0.6 * clamp(spiral, 0.0, 1.0)) * v_color.a * v_life;
  } else if (v_type > 0.5 && v_type < 1.5) {
    // Lightning spark segment (elongated sharp beam)
    float beam = exp(-abs(v_local_pos.y) * 14.0) * (1.0 - abs(v_local_pos.x));
    alpha = beam * v_color.a * v_life;
  } else {
    // Soft radial particle bloom
    alpha = pow(1.0 - dist, 1.6) * v_color.a * v_life;
  }

  // ADR-0012 Theme calibration
  vec3 rgb = v_color.rgb * u_bloom_intensity;
  if (u_theme_mode == 1) {
    // Light mode: deepen core saturation to guarantee >4.5:1 contrast against light background
    rgb = mix(rgb, v_color.rgb * 0.75, 0.25);
  } else if (u_theme_mode == 2) {
    // High-contrast mode: sharp vivid glow
    rgb = v_color.rgb * (u_bloom_intensity + 0.2);
  }

  gl_FragColor = vec4(rgb, alpha);
}
`;

export function initWebGLProgram(gl: WebGLRenderingContext, vsSource: string, fsSource: string): WebGLProgram | null {
  const compile = (type: number, src: string) => {
    const s = gl.createShader(type);
    if (!s) return null;
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { gl.deleteShader(s); return null; }
    return s;
  };
  const vs = compile(gl.VERTEX_SHADER, vsSource);
  const fs = compile(gl.FRAGMENT_SHADER, fsSource);
  if (!vs || !fs) return null;

  const prog = gl.createProgram();
  if (!prog) return null;
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { gl.deleteProgram(prog); return null; }
  return prog;
}

export const PARTICLE_ATTRIB_CONFIGS: [string, string, number, number][] = [
  ['particlePos', 'a_particle_pos', 2, 0],
  ['color', 'a_color', 4, 8],
  ['size', 'a_size', 1, 24],
  ['life', 'a_life', 1, 28],
  ['type', 'a_type', 1, 32],
  ['rotation', 'a_rotation', 1, 36],
];

export function buildParticleVertexData(particles: Particle[]): Float32Array {
  const stride = 10, data = new Float32Array(particles.length * stride);
  for (let i = 0; i < particles.length; i++) {
    const p = particles[i], o = i * stride;
    data[o] = p.x; data[o + 1] = p.y;
    data[o + 2] = p.color[0]; data[o + 3] = p.color[1];
    data[o + 4] = p.color[2]; data[o + 5] = p.color[3];
    data[o + 6] = p.size; data[o + 7] = p.life;
    data[o + 8] = p.type; data[o + 9] = p.rotation;
  }
  return data;
}

export function drawInstancedParticles(
  gl: WebGLRenderingContext, program: WebGLProgram, quadBuffer: WebGLBuffer,
  instancedBuffer: WebGLBuffer, attribs: Record<string, number>, particles: Particle[]
): void {
  if (particles.length === 0) return;
  gl.useProgram(program);
  gl.bindBuffer(gl.ARRAY_BUFFER, instancedBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, buildParticleVertexData(particles), gl.DYNAMIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);
  gl.enableVertexAttribArray(attribs.quadPos);
  gl.vertexAttribPointer(attribs.quadPos, 2, gl.FLOAT, false, 0, 0);

  const ext = gl.getExtension('ANGLE_instanced_arrays');
  if (ext) {
    gl.bindBuffer(gl.ARRAY_BUFFER, instancedBuffer);
    for (const [key, , size, byteOffset] of PARTICLE_ATTRIB_CONFIGS) {
      const loc = attribs[key];
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 40, byteOffset);
      ext.vertexAttribDivisorANGLE(loc, 1);
    }
    ext.drawArraysInstancedANGLE(gl.TRIANGLES, 0, 6, particles.length);
    for (const [key] of PARTICLE_ATTRIB_CONFIGS) ext.vertexAttribDivisorANGLE(attribs[key], 0);
  }
}
