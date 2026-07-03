<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'

interface Props {
  sparkColor?: string
  sparkCount?: number
  sparkRadius?: number
  duration?: number
}

const props = withDefaults(defineProps<Props>(), {
  sparkColor: '#00E5FF',
  sparkCount: 10,
  sparkRadius: 22,
  duration: 420,
})

const canvasEl = ref<HTMLCanvasElement | null>(null)

interface Burst {
  x: number
  y: number
  start: number
}

let ctx: CanvasRenderingContext2D | null = null
let rafId = 0
let ro: ResizeObserver | null = null
let bursts: Burst[] = []
let dpr = 1
let cssW = 0
let cssH = 0
let reduceMotion = false

function resize(): void {
  const canvas = canvasEl.value
  if (!canvas) return
  cssW = window.innerWidth
  cssH = window.innerHeight
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(cssW * dpr)
  canvas.height = Math.round(cssH * dpr)
  canvas.style.width = cssW + 'px'
  canvas.style.height = cssH + 'px'
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

// easeOut for the outward travel
function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

function draw(): void {
  if (!ctx) return
  const c = ctx
  c.clearRect(0, 0, cssW, cssH)
  const now = performance.now()

  bursts = bursts.filter((b) => now - b.start < props.duration)

  for (const b of bursts) {
    const t = (now - b.start) / props.duration
    const eased = easeOut(t)
    const alpha = 1 - t
    c.strokeStyle = props.sparkColor
    c.globalAlpha = alpha
    c.lineWidth = 2
    c.lineCap = 'round'
    for (let i = 0; i < props.sparkCount; i++) {
      const angle = (i / props.sparkCount) * Math.PI * 2
      const inner = eased * props.sparkRadius
      const outer = inner + props.sparkRadius * 0.5 * (1 - t)
      const x1 = b.x + Math.cos(angle) * inner
      const y1 = b.y + Math.sin(angle) * inner
      const x2 = b.x + Math.cos(angle) * outer
      const y2 = b.y + Math.sin(angle) * outer
      c.beginPath()
      c.moveTo(x1, y1)
      c.lineTo(x2, y2)
      c.stroke()
    }
  }
  c.globalAlpha = 1

  if (bursts.length > 0) {
    rafId = requestAnimationFrame(draw)
  } else {
    rafId = 0
  }
}

function onClick(e: MouseEvent): void {
  if (reduceMotion) return
  bursts.push({ x: e.clientX, y: e.clientY, start: performance.now() })
  if (!rafId) rafId = requestAnimationFrame(draw)
}

onMounted(() => {
  const canvas = canvasEl.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  if (!ctx) return

  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  resize()
  ro = new ResizeObserver(() => resize())
  ro.observe(document.documentElement)
  window.addEventListener('resize', resize)
  window.addEventListener('click', onClick, true)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  rafId = 0
  window.removeEventListener('click', onClick, true)
  window.removeEventListener('resize', resize)
  if (ro) {
    ro.disconnect()
    ro = null
  }
  bursts = []
  ctx = null
})
</script>

<template>
  <canvas ref="canvasEl" class="click-spark" aria-hidden="true" />
</template>

<style scoped>
.click-spark {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 2147483000;
}
</style>
