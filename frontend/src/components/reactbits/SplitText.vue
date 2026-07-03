<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

interface Props {
  /** 要展示的文字 */
  text?: string
  /** 切分粒度：按字符 / 按单词 */
  splitType?: 'chars' | 'words'
  /** 每个单位之间的入场间隔(ms) */
  delay?: number
  /** 单个单位的动画时长(ms) */
  duration?: number
  /** 触发方式：进入视口 / 立即 */
  trigger?: 'view' | 'immediate'
  /** 入场时的垂直位移起点(px) */
  yFrom?: number
  /** IntersectionObserver 触发阈值 */
  threshold?: number
  /** 只播放一次 */
  once?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  text: '',
  splitType: 'chars',
  delay: 40,
  duration: 600,
  trigger: 'view',
  yFrom: 24,
  threshold: 0.2,
  once: true,
})

const rootRef = ref<HTMLElement | null>(null)
const played = ref(false)
let observer: IntersectionObserver | null = null

interface Unit {
  text: string
  space: boolean
}

// 中英文混排切分：words 模式下按空白分词但把每个 CJK 字符单列，
// chars 模式下每个字符独立(空格保留为不动的占位)。
const units = computed<Unit[]>(() => {
  const raw = props.text ?? ''
  const result: Unit[] = []
  if (props.splitType === 'words') {
    // 用 Intl.Segmenter(可用时)做词切分，回退到空格切分
    const cjk = /[　-鿿豈-﫿＀-￯]/
    const tokens = raw.split(/(\s+)/)
    for (const tok of tokens) {
      if (tok === '') continue
      if (/^\s+$/.test(tok)) {
        result.push({ text: tok, space: true })
        continue
      }
      // 单词内若含 CJK，逐字拆
      if (cjk.test(tok)) {
        for (const ch of Array.from(tok)) {
          result.push({ text: ch, space: false })
        }
      } else {
        result.push({ text: tok, space: false })
      }
    }
  } else {
    for (const ch of Array.from(raw)) {
      result.push({ text: ch, space: /\s/.test(ch) })
    }
  }
  return result
})

// 参与动画的单位索引(跳过纯空白)，用于连续 stagger
const animOrder = computed(() => {
  const map = new Map<number, number>()
  let n = 0
  units.value.forEach((u, i) => {
    if (!u.space) map.set(i, n++)
  })
  return map
})

const styleVars = computed(() => ({
  '--rb-split-duration': `${props.duration}ms`,
  '--rb-split-y': `${props.yFrom}px`,
}))

function play() {
  if (props.once && played.value) return
  played.value = true
}

onMounted(() => {
  if (props.trigger === 'immediate') {
    play()
    return
  }
  const el = rootRef.value
  if (!el) return
  if (typeof IntersectionObserver === 'undefined') {
    play()
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          play()
          if (props.once && observer) {
            observer.disconnect()
            observer = null
          }
        } else if (!props.once) {
          played.value = false
        }
      }
    },
    { threshold: props.threshold },
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
  <span
    ref="rootRef"
    class="rb-split-text"
    :class="{ 'is-playing': played }"
    :style="styleVars"
    :aria-label="text"
  >
    <template v-for="(u, i) in units" :key="i">
      <span v-if="u.space" class="rb-split-space" aria-hidden="true">{{ u.text }}</span>
      <span
        v-else
        class="rb-split-unit"
        aria-hidden="true"
        :style="{ transitionDelay: `${(animOrder.get(i) ?? 0) * delay}ms` }"
      >{{ u.text }}</span>
    </template>
  </span>
</template>

<style scoped>
.rb-split-text {
  display: inline-block;
  white-space: pre-wrap;
}

.rb-split-unit {
  display: inline-block;
  opacity: 0;
  transform: translateY(var(--rb-split-y));
  transition:
    opacity var(--rb-split-duration) cubic-bezier(0.22, 1, 0.36, 1),
    transform var(--rb-split-duration) cubic-bezier(0.22, 1, 0.36, 1);
  will-change: opacity, transform;
}

.rb-split-space {
  display: inline-block;
  white-space: pre;
}

.is-playing .rb-split-unit {
  opacity: 1;
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .rb-split-unit {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
