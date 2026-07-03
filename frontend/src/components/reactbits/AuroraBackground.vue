<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface Props {
  /** Aurora color ramp (left -> right). 2-5 colors supported, first 3 used as ramp stops. */
  colorStops?: string[]
  /** Height-field amplitude of the aurora ribbons. */
  amplitude?: number
  /** Softness of the aurora edge (0 = crisp, 1 = very soft). */
  blend?: number
  /** Animation speed multiplier. */
  speed?: number
}

const props = withDefaults(defineProps<Props>(), {
  colorStops: () => ['#00E5FF', '#FF5722', '#FFD54F'],
  amplitude: 1,
  blend: 0.5,
  speed: 1,
})

const rootEl = ref<HTMLDivElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)

let gl: WebGLRenderingContext | null = null
let program: WebGLProgram | null = null
let buffer: WebGLBuffer | null = null
let rafId = 0
let startTime = 0
let visible = true
let resizeObs: ResizeObserver | null = null
let intersectObs: IntersectionObserver | null = null
let reducedMotion = false

const uni: Record<string, WebGLUniformLocation | null> = {}

const VERT = `
attribute vec2 position;
varying vec2 vUv;
void main() {
  vUv = position * 0.5 + 0.5;
  gl_Position = vec4(position, 0.0, 1.0);
}
`

const FRAG = `
precision highp float;

varying vec2 vUv;

uniform float uTime;
uniform float uAmplitude;
uniform float uBlend;
uniform vec3 uColor0;
uniform vec3 uColor1;
uniform vec3 uColor2;

vec3 permute(vec3 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}

float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m;
  m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

vec3 colorRamp(float t) {
  t = clamp(t, 0.0, 1.0);
  if (t < 0.5) {
    return mix(uColor0, uColor1, t / 0.5);
  }
  return mix(uColor1, uColor2, (t - 0.5) / 0.5);
}

void main() {
  vec2 uv = vUv;

  vec3 ramp = colorRamp(uv.x);

  // Two layered noise height fields for richer, drifting ribbons.
  float n1 = snoise(vec2(uv.x * 2.0 + uTime * 0.10, uTime * 0.22));
  float n2 = snoise(vec2(uv.x * 4.5 - uTime * 0.06, uTime * 0.15 + 3.7));
  float height = (n1 * 0.6 + n2 * 0.4) * 0.5 * uAmplitude;
  height = exp(height);
  height = (uv.y * 2.0 - height + 0.25);

  float intensity = 0.6 * height;

  float midPoint = 0.20;
  float b = clamp(uBlend, 0.001, 1.0);
  float auroraAlpha = smoothstep(midPoint - b * 0.5, midPoint + b * 0.5, intensity);

  // Soft vertical falloff so the glow lives in the upper/mid band.
  float band = smoothstep(1.05, 0.15, uv.y);
  auroraAlpha *= band;

  vec3 auroraColor = intensity * ramp;
  // Add a gentle bloom highlight.
  float glow = pow(auroraAlpha, 1.5) * 0.35;
  auroraColor += ramp * glow;

  gl_FragColor = vec4(auroraColor * auroraAlpha, auroraAlpha);
}
`

function hexToRgb(hex: string): [number, number, number] {
  let h = hex.trim().replace('#', '')
  if (h.length === 3) {
    h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
  }
  const int = parseInt(h, 16)
  if (Number.isNaN(int) || h.length !== 6) return [1, 1, 1]
  return [((int >> 16) & 255) / 255, ((int >> 8) & 255) / 255, (int & 255) / 255]
}

function rampStops(): [number[], number[], number[]] {
  const src = props.colorStops.length ? props.colorStops : ['#00E5FF', '#FF5722', '#FFD54F']
  const c0 = hexToRgb(src[0])
  const c2 = hexToRgb(src[src.length - 1])
  const c1 = hexToRgb(src[Math.floor((src.length - 1) / 2)] ?? src[0])
  return [c0, c1, c2]
}

function compile(glc: WebGLRenderingContext, type: number, source: string): WebGLShader | null {
  const shader = glc.createShader(type)
  if (!shader) return null
  glc.shaderSource(shader, source)
  glc.compileShader(shader)
  if (!glc.getShaderParameter(shader, glc.COMPILE_STATUS)) {
    glc.deleteShader(shader)
    return null
  }
  return shader
}

function resize() {
  if (!gl || !canvasEl.value || !rootEl.value) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const w = Math.max(1, Math.floor(rootEl.value.clientWidth * dpr))
  const h = Math.max(1, Math.floor(rootEl.value.clientHeight * dpr))
  if (canvasEl.value.width !== w || canvasEl.value.height !== h) {
    canvasEl.value.width = w
    canvasEl.value.height = h
  }
  gl.viewport(0, 0, w, h)
}

function uploadColors() {
  if (!gl || !program) return
  const [c0, c1, c2] = rampStops()
  gl.useProgram(program)
  gl.uniform3fv(uni.uColor0, c0)
  gl.uniform3fv(uni.uColor1, c1)
  gl.uniform3fv(uni.uColor2, c2)
}

function renderFrame(now: number) {
  if (!gl || !program) return
  const t = ((now - startTime) / 1000) * props.speed
  gl.useProgram(program)
  gl.uniform1f(uni.uTime, t)
  gl.uniform1f(uni.uAmplitude, props.amplitude)
  gl.uniform1f(uni.uBlend, props.blend)
  gl.clearColor(0, 0, 0, 0)
  gl.clear(gl.COLOR_BUFFER_BIT)
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
}

function loop(now: number) {
  if (visible) renderFrame(now)
  rafId = requestAnimationFrame(loop)
}

function init() {
  const canvas = canvasEl.value
  if (!canvas) return
  gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: true })
  if (!gl) return

  const vs = compile(gl, gl.VERTEX_SHADER, VERT)
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG)
  if (!vs || !fs) return

  program = gl.createProgram()
  if (!program) return
  gl.attachShader(program, vs)
  gl.attachShader(program, fs)
  gl.linkProgram(program)
  gl.deleteShader(vs)
  gl.deleteShader(fs)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    program = null
    return
  }
  gl.useProgram(program)

  buffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
  const loc = gl.getAttribLocation(program, 'position')
  gl.enableVertexAttribArray(loc)
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)

  uni.uTime = gl.getUniformLocation(program, 'uTime')
  uni.uAmplitude = gl.getUniformLocation(program, 'uAmplitude')
  uni.uBlend = gl.getUniformLocation(program, 'uBlend')
  uni.uColor0 = gl.getUniformLocation(program, 'uColor0')
  uni.uColor1 = gl.getUniformLocation(program, 'uColor1')
  uni.uColor2 = gl.getUniformLocation(program, 'uColor2')

  gl.enable(gl.BLEND)
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)

  uploadColors()
  resize()
  startTime = performance.now()

  if (reducedMotion) {
    renderFrame(startTime)
  } else {
    rafId = requestAnimationFrame(loop)
  }
}

onMounted(() => {
  reducedMotion = typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  init()

  if (rootEl.value && typeof ResizeObserver !== 'undefined') {
    resizeObs = new ResizeObserver(() => {
      resize()
      if (reducedMotion) renderFrame(performance.now())
    })
    resizeObs.observe(rootEl.value)
  }

  if (rootEl.value && typeof IntersectionObserver !== 'undefined') {
    intersectObs = new IntersectionObserver((entries) => {
      visible = entries[0]?.isIntersecting ?? true
    })
    intersectObs.observe(rootEl.value)
  }
})

watch(() => props.colorStops, () => uploadColors(), { deep: true })

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  resizeObs?.disconnect()
  intersectObs?.disconnect()
  if (gl) {
    if (buffer) gl.deleteBuffer(buffer)
    if (program) gl.deleteProgram(program)
    const lose = gl.getExtension('WEBGL_lose_context')
    lose?.loseContext()
  }
  gl = null
  program = null
  buffer = null
})
</script>

<template>
  <div ref="rootEl" class="aurora-bg">
    <canvas ref="canvasEl" aria-hidden="true" />
  </div>
</template>

<style scoped>
.aurora-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0a0e0d;
}
.aurora-bg canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
