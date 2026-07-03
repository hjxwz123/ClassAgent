<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

interface Props {
  distance?: number
  direction?: 'vertical' | 'horizontal'
  reverse?: boolean
  delay?: number
  duration?: number
  once?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  distance: 60,
  direction: 'vertical',
  reverse: false,
  delay: 0,
  duration: 700,
  once: true,
})

const rootRef = ref<HTMLElement | null>(null)
const visible = ref(false)
let observer: IntersectionObserver | null = null
let reduce = false

const initialTransform = computed(() => {
  const d = props.reverse ? -props.distance : props.distance
  return props.direction === 'vertical'
    ? `translateY(${d}px)`
    : `translateX(${d}px)`
})

const style = computed(() => ({
  opacity: visible.value ? 1 : 0,
  transform: visible.value ? 'translate(0, 0)' : initialTransform.value,
  transition: `opacity ${props.duration}ms ease, transform ${props.duration}ms cubic-bezier(0.22, 1, 0.36, 1)`,
  transitionDelay: `${props.delay}ms`,
  willChange: 'opacity, transform',
}))

onMounted(() => {
  reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce) {
    visible.value = true
    return
  }
  const el = rootRef.value
  if (!el) return
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          visible.value = true
          if (props.once && observer) {
            observer.disconnect()
            observer = null
          }
        } else if (!props.once) {
          visible.value = false
        }
      }
    },
    { threshold: 0.1 }
  )
  observer.observe(el)
})

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<template>
  <div ref="rootRef" class="animated-content" :style="style">
    <slot />
  </div>
</template>

<style scoped>
.animated-content {
  display: block;
}
</style>
