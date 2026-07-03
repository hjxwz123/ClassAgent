<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  /** 渐变色数组，横向循环流动 */
  colors?: string[]
  /** 一个完整流动周期的时长(秒) */
  animationSpeed?: number
  /** 是否显示描边光效(在文字外圈叠加一层同款渐变边框) */
  showBorder?: boolean
  /** 是否禁用动画(静止渐变) */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  colors: () => ['#00E5FF', '#FFD54F', '#FF5722', '#00B8D4', '#00E5FF'],
  animationSpeed: 8,
  showBorder: false,
  disabled: false,
})

// 保证首尾同色以实现无缝循环
const stops = computed(() => {
  const c = props.colors.length ? [...props.colors] : ['#00E5FF', '#FF5722']
  if (c.length === 1) c.push(c[0])
  if (c[0] !== c[c.length - 1]) c.push(c[0])
  return c
})

const gradient = computed(() => `linear-gradient(90deg, ${stops.value.join(', ')})`)

const styleVars = computed(() => ({
  '--rb-gt-gradient': gradient.value,
  '--rb-gt-duration': `${props.animationSpeed}s`,
}))
</script>

<template>
  <span
    class="rb-gradient-text"
    :class="{ 'is-static': disabled, 'has-border': showBorder }"
    :style="styleVars"
  >
    <span v-if="showBorder" class="rb-gt-border" aria-hidden="true" />
    <span class="rb-gt-content"><slot /></span>
  </span>
</template>

<style scoped>
.rb-gradient-text {
  position: relative;
  display: inline-flex;
  align-items: center;
  font-weight: 800;
}

.rb-gt-content {
  position: relative;
  z-index: 1;
  background-image: var(--rb-gt-gradient);
  background-size: 300% 100%;
  background-position: 0% 50%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  animation: rb-gt-flow var(--rb-gt-duration) linear infinite;
}

.rb-gt-border {
  position: absolute;
  inset: 0;
  border-radius: 1.25em;
  padding: 2px;
  background-image: var(--rb-gt-gradient);
  background-size: 300% 100%;
  background-position: 0% 50%;
  animation: rb-gt-flow var(--rb-gt-duration) linear infinite;
  /* 只保留边框，镂空内部 */
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  mask-composite: exclude;
  pointer-events: none;
}

.has-border {
  padding: 0.35em 0.9em;
}

.is-static .rb-gt-content,
.is-static .rb-gt-border {
  animation: none;
  background-position: 50% 50%;
}

@keyframes rb-gt-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 100% 50%; }
}

@media (prefers-reduced-motion: reduce) {
  .rb-gt-content,
  .rb-gt-border {
    animation: none;
    background-position: 50% 50%;
  }
}
</style>
