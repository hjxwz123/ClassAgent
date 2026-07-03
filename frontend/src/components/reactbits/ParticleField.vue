<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'

interface Props {
  count?: number
  colors?: string[]
  speed?: number
  linkDistance?: number
  parallax?: number
}

const props = withDefaults(defineProps<Props>(), {
  count: 120,
  colors: () => ['#00E5FF', '#FF5722', '#FFD54F'],
  speed: 0.4,
  linkDistance: 0,
  parallax: 0.03,
})

const rootEl = ref<HTMLDivElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  color: string
  glow: number
}

let ctx: CanvasRenderingContext2D | null = null
let rafId = 0
let ro: ResizeObserver | null = null
let particles: Particle[] = []
let dpr = 1
let cssW = 0
let cssH = 0
// Pointer for parallax (target + smoothed)
let pointerX = 0
let pointerY = 0
let curPX = 0
let curPY = 0
let reduceMotion = false

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function buildParticles(): void {
  const list: Particle[] = []
  const cols = props.colors.length ? props.colors : ['#00E5FF']
  for (let i = 0; i < props.count; i++) {
    list.push({
      x: Math.random() * cssW,
      y: Math.random() * cssH,
      vx: rand(-1, 1) * props.speed,
      vy: rand(-1, 1) * props.speed,
      r: rand(0.8, 2.6),
      color: cols[Math.floor(Math.random() * cols.length)],
      glow: rand(0.35, 1),
    })
  }
  particles = list
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
  if (!particles.length) buildParticles()
}

function hexToRgb(hex: string): [number, number, number] {
  let h = hex.replace('#', '')
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  const n = parseInt(h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function draw(): void {
  if (!ctx) return
  const c = ctx
  c.clearRect(0, 0, cssW, cssH)

  // Smooth parallax
  curPX += (pointerX - curPX) * 0.06
  curPY += (pointerY - curPY) * 0.06
  const offX = curPX * props.parallax * 100
  const offY = curPY * props.parallax * 100

  // Move particles
  if (!reduceMotion) {
    for (const p of particles) {
      p.x += p.vx
      p.y += p.vy
      if (p.x < -20) p.x = cssW + 20
      else if (p.x > cssW + 20) p.x = -20
      if (p.y < -20) p.y = cssH + 20
      else if (p.y > cssH + 20) p.y = -20
    }
  }

  // Links
  if (props.linkDistance > 0) {
    const ld = props.linkDistance
    for (let i = 0; i < particles.length; i++) {
      const a = particles[i]
      const ax = a.x + offX * a.r * 0.5
      const ay = a.y + offY * a.r * 0.5
      for (let j = i + 1; j < particles.length; j++) {
        const b = particles[j]
        const bx = b.x + offX * b.r * 0.5
        const by = b.y + offY * b.r * 0.5
        const dx = ax - bx
        const dy = ay - by
        const dist = Math.hypot(dx, dy)
        if (dist < ld) {
          const alpha = (1 - dist / ld) * 0.35
          const [r, g, bl] = hexToRgb(a.color)
          c.strokeStyle = `rgba(${r},${g},${bl},${alpha})`
          c.lineWidth = 0.6
          c.beginPath()
          c.moveTo(ax, ay)
          c.lineTo(bx, by)
          c.stroke()
        }
      }
    }
  }

  // Glowing dots
  for (const p of particles) {
    const px = p.x + offX * p.r * 0.5
    const py = p.y + offY * p.r * 0.5
    const [r, g, b] = hexToRgb(p.color)
    const grad = c.createRadialGradient(px, py, 0, px, py, p.r * 4)
    grad.addColorStop(0, `rgba(${r},${g},${b},${0.9 * p.glow})`)
    grad.addColorStop(0.4, `rgba(${r},${g},${b},${0.35 * p.glow})`)
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`)
    c.fillStyle = grad
    c.beginPath()
    c.arc(px, py, p.r * 4, 0, Math.PI * 2)
    c.fill()

    c.fillStyle = `rgba(${r},${g},${b},${p.glow})`
    c.beginPath()
    c.arc(px, py, p.r, 0, Math.PI * 2)
    c.fill()
  }

  rafId = requestAnimationFrame(draw)
}

function onPointerMove(e: PointerEvent): void {
  const root = rootEl.value
  if (!root) return
  const rect = root.getBoundingClientRect()
  pointerX = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointerY = ((e.clientY - rect.top) / rect.height) * 2 - 1
}

onMounted(() => {
  const canvas = canvasEl.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  if (!ctx) return

  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  resize()
  ro = new ResizeObserver(() => resize())
  if (rootEl.value) ro.observe(rootEl.value)
  window.addEventListener('pointermove', onPointerMove, { passive: true })

  rafId = requestAnimationFrame(draw)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  window.removeEventListener('pointermove', onPointerMove)
  if (ro) {
    ro.disconnect()
    ro = null
  }
  particles = []
  ctx = null
})
</script>

<template>
  <div ref="rootEl" class="particle-field">
    <canvas ref="canvasEl" aria-hidden="true" />
  </div>
</template>

<style scoped>
.particle-field {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.particle-field canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
