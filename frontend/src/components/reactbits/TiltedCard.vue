<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Props {
  rotateAmplitude?: number
  scale?: number
  glare?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  rotateAmplitude: 12,
  scale: 1.05,
  glare: true,
})

const cardRef = ref<HTMLElement | null>(null)
const rotateX = ref(0)
const rotateY = ref(0)
const currentScale = ref(1)
const glareX = ref(50)
const glareY = ref(50)
const glareOpacity = ref(0)

let reduce = false

function onMove(e: MouseEvent) {
  if (reduce) return
  const el = cardRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const px = (e.clientX - rect.left) / rect.width
  const py = (e.clientY - rect.top) / rect.height
  rotateY.value = (px - 0.5) * 2 * props.rotateAmplitude
  rotateX.value = (0.5 - py) * 2 * props.rotateAmplitude
  glareX.value = px * 100
  glareY.value = py * 100
}

function onEnter() {
  if (reduce) return
  currentScale.value = props.scale
  glareOpacity.value = props.glare ? 1 : 0
}

function onLeave() {
  rotateX.value = 0
  rotateY.value = 0
  currentScale.value = 1
  glareOpacity.value = 0
}

onMounted(() => {
  reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
})
</script>

<template>
  <div
    ref="cardRef"
    class="tilted-card"
    @mousemove="onMove"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <div
      class="tilted-card__inner"
      :style="{
        transform: `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${currentScale})`,
      }"
    >
      <div class="tilted-card__content">
        <slot />
      </div>
      <div
        v-if="glare"
        class="tilted-card__glare"
        aria-hidden="true"
        :style="{
          opacity: glareOpacity,
          background: `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255,255,255,0.35), transparent 55%)`,
        }"
      />
    </div>
  </div>
</template>

<style scoped>
.tilted-card {
  perspective: 900px;
  display: inline-block;
}

.tilted-card__inner {
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.25s cubic-bezier(0.23, 1, 0.32, 1);
  border-radius: 16px;
  overflow: hidden;
  will-change: transform;
}

.tilted-card__content {
  position: relative;
  z-index: 0;
}

.tilted-card__glare {
  position: absolute;
  inset: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
  z-index: 1;
  mix-blend-mode: overlay;
}

@media (prefers-reduced-motion: reduce) {
  .tilted-card__inner {
    transition: none;
    transform: none !important;
  }
  .tilted-card__glare {
    display: none;
  }
}
</style>
