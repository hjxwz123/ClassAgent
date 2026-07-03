<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface Props {
  /** Number of light beams. */
  beamCount?: number
  /** Beam colors, cycled across the beams. */
  colors?: string[]
  /** Flow speed. */
  speed?: number
  /** Tilt angle in degrees. */
  angle?: number
}

const props = withDefaults(defineProps<Props>(), {
  beamCount: 12,
  colors: () => ['#00E5FF', '#FF5722', '#FFD54F'],
  speed: 2,
  angle: 30,
})

const rootEl = ref<HTMLDivElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)

let ctx: CanvasRenderingContext2D | null = null
let rafId = 0
let lastTime = 0
let visible = true
let resizeObs: ResizeObserver | null = null
let intersectObs: IntersectionObserver | null = null
let reducedMotion = false
let dpr = 1

interface Beam {
  pos: number       // 0..1 position across the perpendicular axis
  width: number     // beam thickness in px (css)
  drift: number     // drift speed across the axis
  phase: number     // flow phase along the beam
  flow: number      // flow speed along the beam
  color: [number, number, number]
  intensity: number // 0..1 base opacity
  pulse: number     // pulsing frequency
}

let beams: Beam[] = []
let accumulated = 0

function hexToRgb(hex: string): [number, number, number] {
  let h = hex.trim().replace('#', '')
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
  const int = parseInt(h, 16)
  if (Number.isNaN(int) || h.length !== 6) return [0, 229, 255]
  return [(int >> 16) & 255, (int >> 8) & 255, int & 255]
}

function buildBeams() {
  const palette = (props.colors.length ? props.colors : ['#00E5FF', '#FF5722', '#FFD54F']).map(hexToRgb)
  const n = Math.max(1, Math.floor(props.beamCount))
  beams = []
  for (let i = 0; i < n; i++) {
    // Deterministic-ish spread so beams are evenly distributed but varied.
    const r = (seed: number) => {
      const x = Math.sin(seed * 127.1 + i * 311.7) * 43758.5453
      return x - Math.floor(x)
    }
    beams.push({
      pos: (i + 0.5) / n + (r(1) - 0.5) * (0.6 / n),
      width: 40 + r(2) * 120,
      drift: (r(3) - 0.5) * 0.04,
      phase: r(4) * Math.PI * 2,
      flow: 0.4 + r(5) * 1.2,
      color: palette[i % palette.length],
      intensity: 0.25 + r(6) * 0.45,
      pulse: 0.3 + r(7) * 0.8,
    })
  }
}

function resize() {
  if (!canvasEl.value || !rootEl.value) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  const w = Math.max(1, Math.floor(rootEl.value.clientWidth * dpr))
  const h = Math.max(1, Math.floor(rootEl.value.clientHeight * dpr))
  if (canvasEl.value.width !== w || canvasEl.value.height !== h) {
    canvasEl.value.width = w
    canvasEl.value.height = h
  }
}

function renderFrame(elapsed: number) {
  const canvas = canvasEl.value
  if (!ctx || !canvas) return
  const W = canvas.width
  const H = canvas.height
  const rad = (props.angle * Math.PI) / 180

  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.clearRect(0, 0, W, H)
  // Deep base tint.
  ctx.fillStyle = '#0a0e0d'
  ctx.fillRect(0, 0, W, H)

  // Work in a rotated frame centered on the canvas.
  const cx = W / 2
  const cy = H / 2
  ctx.translate(cx, cy)
  ctx.rotate(rad)
  ctx.globalCompositeOperation = 'lighter'

  // Diagonal length so rotated beams always cover the canvas.
  const diag = Math.sqrt(W * W + H * H)
  const half = diag / 2
  const span = diag * 1.1

  for (const beam of beams) {
    // Drift the beam across the perpendicular axis, wrapping in 0..1.
    let p = beam.pos + beam.drift * elapsed
    p = p - Math.floor(p)
    const x = (p - 0.5) * span
    const w = beam.width * dpr

    // Flowing highlight travels along the beam length.
    const flow = ((beam.phase + elapsed * beam.flow) % 1 + 1) % 1
    const pulse = 0.65 + 0.35 * Math.sin(elapsed * beam.pulse + beam.phase)
    const [r, g, b] = beam.color
    const alpha = beam.intensity * pulse

    // Cross-beam soft gradient (glow falloff across width).
    const grad = ctx.createLinearGradient(x - w / 2, 0, x + w / 2, 0)
    grad.addColorStop(0, `rgba(${r},${g},${b},0)`)
    grad.addColorStop(0.5, `rgba(${r},${g},${b},${alpha})`)
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`)
    ctx.fillStyle = grad
    ctx.fillRect(x - w / 2, -half, w, span)

    // Bright travelling core along the length for a volumetric feel.
    const coreY = (flow - 0.5) * span
    const coreLen = span * 0.35
    const lg = ctx.createLinearGradient(0, coreY - coreLen / 2, 0, coreY + coreLen / 2)
    lg.addColorStop(0, `rgba(${r},${g},${b},0)`)
    lg.addColorStop(0.5, `rgba(255,255,255,${alpha * 0.35})`)
    lg.addColorStop(1, `rgba(${r},${g},${b},0)`)
    ctx.fillStyle = lg
    ctx.fillRect(x - w / 2, coreY - coreLen / 2, w, coreLen)
  }

  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.globalCompositeOperation = 'source-over'

  // Vignette to focus the glow.
  const vg = ctx.createRadialGradient(cx, cy, Math.min(W, H) * 0.2, cx, cy, Math.max(W, H) * 0.75)
  vg.addColorStop(0, 'rgba(10,14,13,0)')
  vg.addColorStop(1, 'rgba(10,14,13,0.65)')
  ctx.fillStyle = vg
  ctx.fillRect(0, 0, W, H)
}

function loop(now: number) {
  if (!lastTime) lastTime = now
  const dt = (now - lastTime) / 1000
  lastTime = now
  if (visible) {
    accumulated += dt * props.speed * 0.15
    renderFrame(accumulated)
  }
  rafId = requestAnimationFrame(loop)
}

function init() {
  const canvas = canvasEl.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  if (!ctx) return
  buildBeams()
  resize()
  if (reducedMotion) {
    accumulated = 5
    renderFrame(accumulated)
  } else {
    lastTime = 0
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
      if (reducedMotion) renderFrame(accumulated)
    })
    resizeObs.observe(rootEl.value)
  }

  if (rootEl.value && typeof IntersectionObserver !== 'undefined') {
    intersectObs = new IntersectionObserver((entries) => {
      visible = entries[0]?.isIntersecting ?? true
      if (visible) lastTime = 0
    })
    intersectObs.observe(rootEl.value)
  }
})

watch(
  () => [props.beamCount, props.colors] as const,
  () => {
    buildBeams()
    if (reducedMotion) renderFrame(accumulated)
  },
  { deep: true },
)

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  resizeObs?.disconnect()
  intersectObs?.disconnect()
  ctx = null
})
</script>

<template>
  <div ref="rootEl" class="beams-bg">
    <canvas ref="canvasEl" aria-hidden="true" />
  </div>
</template>

<style scoped>
.beams-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0a0e0d;
}
.beams-bg canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
