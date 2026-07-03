<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

interface Props {
  /** 目标文字 */
  text: string
  /** 每帧间隔毫秒 */
  speed?: number
  /** 触发方式：进入视口 or 悬停 */
  trigger?: 'view' | 'hover'
  /** 乱码字符集 */
  characters?: string
  /** 逐位揭示的最大迭代次数（每个字符经历多少次乱码后定位） */
  maxIterations?: number
  /** 揭示方向 */
  revealDirection?: 'start' | 'end' | 'center'
}

const props = withDefaults(defineProps<Props>(), {
  speed: 45,
  trigger: 'view',
  characters: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!<>-_\\/[]{}—=+*^?#________',
  maxIterations: 12,
  revealDirection: 'start',
})

const rootRef = ref<HTMLElement | null>(null)
const display = ref<string>('')
const revealed = ref<Set<number>>(new Set())

let timer: ReturnType<typeof setInterval> | null = null
let observer: IntersectionObserver | null = null
let iteration = 0
let hasRun = false

const prefersReduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

const randChar = () =>
  props.characters[Math.floor(Math.random() * props.characters.length)] || ' '

function revealOrder(index: number, total: number): number {
  // 返回该字符应在第几"批"被解密（0 = 最先）
  if (props.revealDirection === 'end') return total - 1 - index
  if (props.revealDirection === 'center') {
    const mid = (total - 1) / 2
    return Math.round(Math.abs(index - mid))
  }
  return index
}

function stop() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function scramble() {
  const target = props.text
  const total = target.length
  const out: string[] = []
  for (let i = 0; i < total; i++) {
    const ch = target[i]
    if (ch === ' ') {
      out.push(' ')
      continue
    }
    if (revealed.value.has(i)) {
      out.push(ch)
    } else {
      out.push(randChar())
    }
  }
  display.value = out.join('')
}

function run() {
  const target = props.text
  const total = target.length

  if (prefersReduced()) {
    display.value = target
    return
  }

  stop()
  iteration = 0
  revealed.value = new Set()

  // 每个字符设定其"解密"所需的迭代阈值
  const thresholds: number[] = []
  for (let i = 0; i < total; i++) {
    thresholds[i] = revealOrder(i, total)
  }
  const maxOrder = Math.max(0, ...thresholds)
  const stepsPerOrder = Math.max(1, Math.floor(props.maxIterations / (maxOrder + 1)) || 1)

  timer = setInterval(() => {
    iteration++
    for (let i = 0; i < total; i++) {
      const unlockAt = (thresholds[i] + 1) * stepsPerOrder
      if (iteration >= unlockAt) revealed.value.add(i)
    }
    scramble()

    if (revealed.value.size >= total - target.split('').filter((c) => c === ' ').length) {
      // 所有非空格已揭示
      const allDone = target.split('').every((c, i) => c === ' ' || revealed.value.has(i))
      if (allDone) {
        display.value = target
        stop()
      }
    }
  }, Math.max(10, props.speed))
}

function trigger() {
  if (hasRun && props.trigger === 'view') return
  hasRun = true
  run()
}

function onEnter() {
  if (props.trigger === 'hover') run()
}
function onLeave() {
  if (props.trigger === 'hover') {
    stop()
    display.value = props.text
    revealed.value = new Set(props.text.split('').map((_, i) => i))
  }
}

onMounted(() => {
  display.value = props.text
  if (props.trigger === 'view') {
    if ('IntersectionObserver' in window && rootRef.value) {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              trigger()
              if (observer) observer.disconnect()
            }
          })
        },
        { threshold: 0.3 },
      )
      observer.observe(rootRef.value)
    } else {
      trigger()
    }
  }
})

watch(
  () => props.text,
  () => {
    hasRun = false
    display.value = props.text
    if (props.trigger === 'view') trigger()
  },
)

onBeforeUnmount(() => {
  stop()
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<template>
  <span
    ref="rootRef"
    class="decrypted-text"
    :aria-label="text"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <span aria-hidden="true" class="decrypted-text__inner">{{ display }}</span>
  </span>
</template>

<style scoped>
.decrypted-text {
  display: inline-block;
  font-variant-ligatures: none;
  white-space: pre-wrap;
}
.decrypted-text__inner {
  font-family: inherit;
}
</style>
