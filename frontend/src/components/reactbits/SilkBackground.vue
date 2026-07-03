<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface Props {
  /** Base silk tint. */
  color?: string
  /** Flow speed. */
  speed?: number
  /** Pattern scale (higher = finer folds). */
  scale?: number
  /** Grain / noise intensity. */
  noiseIntensity?: number
}

const props = withDefaults(defineProps<Props>(), {
  color: '#00B8D4',
  speed: 5,
  scale: 1,
  noiseIntensity: 1.5,
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
uniform float uSpeed;
uniform float uScale;
uniform float uNoiseIntensity;
uniform vec3 uColor;
uniform vec2 uResolution;

const float e = 2.71828182845904523536;

float noise(vec2 texCoord) {
  float G = e;
  vec2 r = (G * sin(G * texCoord));
  return fract(r.x * r.y * (1.0 + texCoord.x));
}

vec2 rotateUvs(vec2 uv, float angle) {
  float c = cos(angle);
  float s = sin(angle);
  mat2 rot = mat2(c, -s, s, c);
  return rot * uv;
}

void main() {
  // Keep folds aspect-correct.
  vec2 aspect = vec2(uResolution.x / max(uResolution.y, 1.0), 1.0);
  float rnd = noise(gl_FragCoord.xy);
  vec2 uv = rotateUvs(vUv * aspect * uScale, 3.0);
  vec2 tex = uv;
  float tOffset = uSpeed * uTime;

  tex.y += 0.03 * sin(8.0 * tex.x - tOffset);

  float pattern = 0.6 +
    0.4 * sin(5.0 * (tex.x + tex.y +
                     cos(3.0 * tex.x + 5.0 * tex.y) +
                     0.02 * tOffset) +
              sin(20.0 * (tex.x + tex.y - 0.1 * tOffset)));

  vec3 col = uColor * pattern - (rnd / 15.0) * uNoiseIntensity;
  gl_FragColor = vec4(col, 1.0);
}
`

function hexToRgb(hex: string): [number, number, number] {
  let h = hex.trim().replace('#', '')
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
  const int = parseInt(h, 16)
  if (Number.isNaN(int) || h.length !== 6) return [0, 0.72, 0.83]
  return [((int >> 16) & 255) / 255, ((int >> 8) & 255) / 255, (int & 255) / 255]
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
  if (program) {
    gl.useProgram(program)
    gl.uniform2f(uni.uResolution, w, h)
  }
}

function uploadColor() {
  if (!gl || !program) return
  gl.useProgram(program)
  gl.uniform3fv(uni.uColor, hexToRgb(props.color))
}

function renderFrame(now: number) {
  if (!gl || !program) return
  const t = (now - startTime) / 1000
  gl.useProgram(program)
  gl.uniform1f(uni.uTime, t)
  gl.uniform1f(uni.uSpeed, props.speed * 0.1)
  gl.uniform1f(uni.uScale, props.scale)
  gl.uniform1f(uni.uNoiseIntensity, props.noiseIntensity)
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
}

function loop(now: number) {
  if (visible) renderFrame(now)
  rafId = requestAnimationFrame(loop)
}

function init() {
  const canvas = canvasEl.value
  if (!canvas) return
  gl = canvas.getContext('webgl', { alpha: false, antialias: true })
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
  uni.uSpeed = gl.getUniformLocation(program, 'uSpeed')
  uni.uScale = gl.getUniformLocation(program, 'uScale')
  uni.uNoiseIntensity = gl.getUniformLocation(program, 'uNoiseIntensity')
  uni.uColor = gl.getUniformLocation(program, 'uColor')
  uni.uResolution = gl.getUniformLocation(program, 'uResolution')

  uploadColor()
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

watch(() => props.color, () => {
  uploadColor()
  if (reducedMotion) renderFrame(performance.now())
})

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
  <div ref="rootEl" class="silk-bg">
    <canvas ref="canvasEl" aria-hidden="true" />
  </div>
</template>

<style scoped>
.silk-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0a0e0d;
}
.silk-bg canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
