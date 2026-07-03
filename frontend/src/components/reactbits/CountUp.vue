<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'

interface Props {
  /** 目标值 */
  to: number
  /** 起始值 */
  from?: number
  /** 时长(ms) */
  duration?: number
  /** 千分位分隔符，如 ',' */
  separator?: string
  /** 前缀，如 '$' */
  prefix?: string
  /** 后缀，如 '%' */
  suffix?: string
  /** 小数位数 */
  decimals?: number
  /** 小数点符号 */
  decimalSep?: string
}

const props = withDefaults(defineProps<Props>(), {
  from: 0,
  duration: 1800,
  separator: '',
  prefix: '',
  suffix: '',
  decimals: 0,
  decimalSep: '.',
})

const rootRef = ref<HTMLElement | null>(null)
const value = ref(props.from)

let raf = 0
let observer: IntersectionObserver | null = null
let started = false

const prefersReduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

// easeOutExpo
const ease = (t: number) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t))

function format(n: number): string {
  const fixed = n.toFixed(Math.max(0, props.decimals))
  const [intPartRaw, decPart] = fixed.split('.')
  const neg = intPartRaw.startsWith('-')
  const intPart = neg ? intPartRaw.slice(1) : intPartRaw
  let grouped = intPart
  if (props.separator) {
    grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, props.separator)
  }
  let body = grouped
  if (props.decimals > 0 && decPart !== undefined) {
    body += props.decimalSep + decPart
  }
  return `${props.prefix}${neg ? '-' : ''}${body}${props.suffix}`
}

const text = computed(() => format(value.value))

function animate() {
  if (started) return
  started = true

  if (prefersReduced()) {
    value.value = props.to
    return
  }

  const start = performance.now()
  const dur = Math.max(1, props.duration)
  const a = props.from
  const b = props.to

  const tick = (now: number) => {
    const p = Math.min(1, (now - start) / dur)
    value.value = a + (b - a) * ease(p)
    if (p < 1) {
      raf = requestAnimationFrame(tick)
    } else {
      value.value = b
    }
  }
  raf = requestAnimationFrame(tick)
}

onMounted(() => {
  value.value = props.from
  if ('IntersectionObserver' in window && rootRef.value) {
    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            animate()
            if (observer) observer.disconnect()
          }
        })
      },
      { threshold: 0.4 },
    )
    observer.observe(rootRef.value)
  } else {
    animate()
  }
})

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<template>
  <span ref="rootRef" class="count-up">{{ text }}</span>
</template>

<style scoped>
.count-up {
  display: inline-block;
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
}
</style>
