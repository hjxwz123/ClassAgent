<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'

interface Props {
  /** 轮播词组 */
  texts: string[]
  /** 每个词停留时间(ms) */
  interval?: number
  /** 切换动画时长(ms) */
  duration?: number
  /** 是否逐字符错落进入 */
  splitByChar?: boolean
  /** 逐字符错落步进(ms) */
  stagger?: number
}

const props = withDefaults(defineProps<Props>(), {
  interval: 2200,
  duration: 500,
  splitByChar: true,
  stagger: 28,
})

const index = ref(0)
const current = computed(() => props.texts[index.value] ?? '')
const chars = computed(() => current.value.split(''))

let timer: ReturnType<typeof setInterval> | null = null

const prefersReduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

const durMs = computed(() => `${props.duration}ms`)

function next() {
  index.value = (index.value + 1) % Math.max(1, props.texts.length)
}

onMounted(() => {
  if (props.texts.length <= 1) return
  if (prefersReduced()) return
  timer = setInterval(next, Math.max(props.duration + 200, props.interval))
})

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<template>
  <span class="rotating-text" :style="{ '--dur': durMs }">
    <span class="rotating-text__sr">{{ current }}</span>
    <transition-group
      tag="span"
      class="rotating-text__viewport"
      name="rt"
      aria-hidden="true"
    >
      <span :key="index" class="rotating-text__word">
        <template v-if="splitByChar">
          <span
            v-for="(c, i) in chars"
            :key="i"
            class="rotating-text__char"
            :style="{ transitionDelay: `${i * stagger}ms`, animationDelay: `${i * stagger}ms` }"
            >{{ c === ' ' ? ' ' : c }}</span
          >
        </template>
        <template v-else>{{ current }}</template>
      </span>
    </transition-group>
  </span>
</template>

<style scoped>
.rotating-text {
  display: inline-flex;
  position: relative;
  vertical-align: bottom;
  overflow: hidden;
  line-height: 1.2;
}
.rotating-text__viewport {
  display: inline-grid;
  position: relative;
}
.rotating-text__word {
  grid-area: 1 / 1;
  display: inline-flex;
  white-space: pre;
  will-change: transform, opacity;
}
.rotating-text__char {
  display: inline-block;
  will-change: transform, opacity;
}
.rotating-text__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/* 逐字符：进入从下方滑入淡入，离开向上滑出淡出 */
.rt-enter-active .rotating-text__char {
  animation: rt-in var(--dur) cubic-bezier(0.22, 1, 0.36, 1) both;
}
.rt-leave-active .rotating-text__char {
  animation: rt-out var(--dur) cubic-bezier(0.55, 0, 0.55, 1) both;
}
.rt-leave-active {
  position: absolute;
  inset: 0;
}

@keyframes rt-in {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
@keyframes rt-out {
  from {
    transform: translateY(0);
    opacity: 1;
  }
  to {
    transform: translateY(-100%);
    opacity: 0;
  }
}

/* 整体切换（splitByChar=false）时给 word 加过渡 */
.rt-enter-active .rotating-text__word,
.rt-leave-active .rotating-text__word {
  transition: transform var(--dur) cubic-bezier(0.22, 1, 0.36, 1),
    opacity var(--dur) ease;
}
.rt-enter-from .rotating-text__word {
  transform: translateY(100%);
  opacity: 0;
}
.rt-leave-to .rotating-text__word {
  transform: translateY(-100%);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .rt-enter-active .rotating-text__char,
  .rt-leave-active .rotating-text__char,
  .rt-enter-active .rotating-text__word,
  .rt-leave-active .rotating-text__word {
    animation: none;
    transition: none;
  }
}
</style>
