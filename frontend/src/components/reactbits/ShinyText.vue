<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  /** 直接传文字(也可用默认插槽) */
  text?: string
  /** 一次高光扫过的周期(秒) */
  speed?: number
  /** 关闭高光动画 */
  disabled?: boolean
  /** 基础文字颜色 */
  baseColor?: string
  /** 高光颜色 */
  shineColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  text: '',
  speed: 4,
  disabled: false,
  baseColor: 'rgba(180, 200, 205, 0.55)',
  shineColor: '#ffffff',
})

const styleVars = computed(() => ({
  '--rb-shiny-duration': `${props.speed}s`,
  '--rb-shiny-base': props.baseColor,
  '--rb-shiny-shine': props.shineColor,
}))
</script>

<template>
  <span
    class="rb-shiny-text"
    :class="{ 'is-disabled': disabled }"
    :style="styleVars"
  ><slot>{{ text }}</slot></span>
</template>

<style scoped>
.rb-shiny-text {
  display: inline-block;
  color: var(--rb-shiny-base);
  background-image: linear-gradient(
    120deg,
    transparent 40%,
    var(--rb-shiny-shine) 50%,
    transparent 60%
  );
  background-size: 200% 100%;
  background-repeat: no-repeat;
  background-position: 150% 0;
  -webkit-background-clip: text;
  background-clip: text;
  animation: rb-shiny-sweep var(--rb-shiny-duration) linear infinite;
}

.is-disabled {
  animation: none;
  background: none;
  -webkit-text-fill-color: currentColor;
}

@keyframes rb-shiny-sweep {
  0% { background-position: 150% 0; }
  100% { background-position: -50% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .rb-shiny-text {
    animation: none;
    background: none;
  }
}
</style>
