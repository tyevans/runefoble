/**
 * WebGL Shaders for tactical particle magic and spell archetype VFX.
 * Incorporates ADR-0012 accessible dark and light mode bloom calibrations.
 */

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

export function initWebGLProgram(
  gl: WebGLRenderingContext,
  vsSource: string,
  fsSource: string
): WebGLProgram | null {
  const vs = gl.createShader(gl.VERTEX_SHADER);
  if (!vs) return null;
  gl.shaderSource(vs, vsSource);
  gl.compileShader(vs);
  if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
    gl.deleteShader(vs);
    return null;
  }

  const fs = gl.createShader(gl.FRAGMENT_SHADER);
  if (!fs) {
    gl.deleteShader(vs);
    return null;
  }
  gl.shaderSource(fs, fsSource);
  gl.compileShader(fs);
  if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    return null;
  }

  const program = gl.createProgram();
  if (!program) {
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    return null;
  }
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    gl.deleteProgram(program);
    return null;
  }

  return program;
}
