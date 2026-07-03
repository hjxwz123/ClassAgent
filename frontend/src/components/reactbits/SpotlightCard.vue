<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

interface Props {
  spotlightColor?: string
  radius?: number
}

const props = withDefaults(defineProps<Props>(), {
  spotlightColor: 'rgba(0,229,255,0.25)',
  radius: 320,
})

const cardRef = ref<HTMLElement | null>(null)
const x = ref(0)
const y = ref(0)
const opacity = ref(0)

let reduce = false

function onMove(e: MouseEvent) {
  if (reduce) return
  const el = cardRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  x.value = e.clientX - rect.left
  y.value = e.clientY - rect.top
}

function onEnter() {
  if (reduce) return
  opacity.value = 1
}

function onLeave() {
  opacity.value = 0
}

onMounted(() => {
  reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
})

onBeforeUnmount(() => {
  // listeners are bound in template, Vue cleans them up automatically
})
</script>

<template>
  <div
    ref="cardRef"
    class="spotlight-card"
    @mousemove="onMove"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <div
      class="spotlight-card__glow"
      aria-hidden="true"
      :style="{
        opacity,
        background: `radial-gradient(${radius}px circle at ${x}px ${y}px, ${spotlightColor}, transparent 70%)`,
      }"
    />
    <div class="spotlight-card__content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.spotlight-card {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(16, 22, 24, 0.6);
  padding: 1.75rem;
  isolation: isolate;
}

.spotlight-card__glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  transition: opacity 0.4s ease;
  z-index: 0;
}

.spotlight-card__content {
  position: relative;
  z-index: 1;
}

@media (prefers-reduced-motion: reduce) {
  .spotlight-card__glow {
    display: none;
  }
}
</style>
