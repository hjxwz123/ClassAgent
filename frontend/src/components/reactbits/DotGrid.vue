<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'

interface Props {
  dotColor?: string
  activeColor?: string
  gap?: number
  dotSize?: number
  proximity?: number
}

const props = withDefaults(defineProps<Props>(), {
  dotColor: '#1b2a2e',
  activeColor: '#00E5FF',
  gap: 28,
  dotSize: 2,
  proximity: 120,
})

const rootEl = ref<HTMLDivElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)

interface Dot {
  ox: number
  oy: number
  x: number
  y: number
  size: number
  mix: number
}

let ctx: CanvasRenderingContext2D | null = null
let rafId = 0
let ro: ResizeObserver | null = null
let dots: Dot[] = []
let dpr = 1
let cssW = 0
let cssH = 0
let mouseX = -9999
let mouseY = -9999
let reduceMotion = false

function hexToRgb(hex: string): [number, number, number] {
  let h = hex.replace('#', '')
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  const n = parseInt(h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

let baseRgb: [number, number, number] = [27, 42, 46]
let activeRgb: [number, number, number] = [0, 229, 255]

function buildDots(): void {
  const list: Dot[] = []
  const gap = props.gap
  const cols = Math.floor(cssW / gap)
  const rows = Math.floor(cssH / gap)
  const offX = (cssW - (cols - 1) * gap) / 2
  const offY = (cssH - (rows - 1) * gap) / 2
  for (let r = 0; r < rows; r++) {
    for (let cc = 0; cc < cols; cc++) {
      const x = offX + cc * gap
      const y = offY + r * gap
      list.push({ ox: x, oy: y, x, y, size: props.dotSize, mix: 0 })
    }
  }
  dots = list
}

function resize(): void {
  const root = rootEl.value
  const canvas = canvasEl.value
  if (!root || !canvas) return
  cssW = root.clientWidth || 1
  cssH = root.clientHeight || 1
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(cssW * dpr)
  canvas.height = Math.round(cssH * dpr)
  canvas.style.width = cssW + 'px'
  canvas.style.height = cssH + 'px'
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  buildDots()
}

function draw(): void {
  if (!ctx) return
  const c = ctx
  c.clearRect(0, 0, cssW, cssH)
  const prox = props.proximity
  const prox2 = prox * prox

  for (const d of dots) {
    const dx = d.ox - mouseX
    const dy = d.oy - mouseY
    const dist2 = dx * dx + dy * dy

    let targetMix = 0
    let pushX = 0
    let pushY = 0
    if (dist2 < prox2) {
      const dist = Math.sqrt(dist2) || 0.0001
      const falloff = 1 - dist / prox
      targetMix = falloff
      // push the dot away from cursor
      const push = falloff * 14
      pushX = (dx / dist) * push
      pushY = (dy / dist) * push
    }

    // Smooth toward target (spring-like return)
    const ease = reduceMotion ? 1 : 0.15
    d.mix += (targetMix - d.mix) * ease
    const tx = d.ox + pushX
    const ty = d.oy + pushY
    d.x += (tx - d.x) * (reduceMotion ? 1 : 0.18)
    d.y += (ty - d.y) * (reduceMotion ? 1 : 0.18)

    const size = props.dotSize + d.mix * props.dotSize * 2.2
    const m = d.mix
    const r = Math.round(baseRgb[0] + (activeRgb[0] - baseRgb[0]) * m)
    const g = Math.round(baseRgb[1] + (activeRgb[1] - baseRgb[1]) * m)
    const b = Math.round(baseRgb[2] + (activeRgb[2] - baseRgb[2]) * m)

    if (m > 0.05) {
      c.shadowColor = `rgba(${activeRgb[0]},${activeRgb[1]},${activeRgb[2]},${m})`
      c.shadowBlur = 8 * m
    } else {
      c.shadowBlur = 0
    }
    c.fillStyle = `rgb(${r},${g},${b})`
    c.beginPath()
    c.arc(d.x, d.y, size, 0, Math.PI * 2)
    c.fill()
  }
  c.shadowBlur = 0

  rafId = requestAnimationFrame(draw)
}

function onPointerMove(e: PointerEvent): void {
  const root = rootEl.value
  if (!root) return
  const rect = root.getBoundingClientRect()
  mouseX = e.clientX - rect.left
  mouseY = e.clientY - rect.top
}

function onPointerLeave(): void {
  mouseX = -9999
  mouseY = -9999
}

onMounted(() => {
  const canvas = canvasEl.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  if (!ctx) return

  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  baseRgb = hexToRgb(props.dotColor)
  activeRgb = hexToRgb(props.activeColor)

  resize()
  ro = new ResizeObserver(() => resize())
  if (rootEl.value) ro.observe(rootEl.value)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
  window.addEventListener('pointerleave', onPointerLeave)

  rafId = requestAnimationFrame(draw)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerleave', onPointerLeave)
  if (ro) {
    ro.disconnect()
    ro = null
  }
  dots = []
  ctx = null
})
</script>

<template>
  <div ref="rootEl" class="dot-grid">
    <canvas ref="canvasEl" aria-hidden="true" />
  </div>
</template>

<style scoped>
.dot-grid {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.dot-grid canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
