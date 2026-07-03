<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  color?: string
  speed?: number
  thickness?: number
  as?: 'button' | 'a' | 'div'
}

const props = withDefaults(defineProps<Props>(), {
  color: '#00E5FF',
  speed: 6,
  thickness: 1,
  as: 'div',
})

const styleVars = computed(() => ({
  '--sb-color': props.color,
  '--sb-speed': `${props.speed}s`,
  '--sb-thickness': `${props.thickness}px`,
}))
</script>

<template>
  <component :is="as" class="star-border" :style="styleVars">
    <span class="star-border__glow star-border__glow--top" aria-hidden="true" />
    <span class="star-border__glow star-border__glow--bottom" aria-hidden="true" />
    <span class="star-border__content">
      <slot />
    </span>
  </component>
</template>

<style scoped>
.star-border {
  position: relative;
  display: inline-block;
  overflow: hidden;
  border-radius: 14px;
  padding: var(--sb-thickness);
  background: rgba(10, 14, 13, 0.9);
  border: none;
  cursor: pointer;
  isolation: isolate;
  color: inherit;
  font: inherit;
  text-decoration: none;
}

.star-border__glow {
  position: absolute;
  width: 300%;
  height: 50%;
  opacity: 0.7;
  border-radius: 50%;
  z-index: 0;
  filter: blur(2px);
}

.star-border__glow--top {
  top: -12px;
  right: -250%;
  background: radial-gradient(circle, var(--sb-color), transparent 12%);
  animation: sb-move-top var(--sb-speed) linear infinite alternate;
}

.star-border__glow--bottom {
  bottom: -12px;
  left: -250%;
  background: radial-gradient(circle, var(--sb-color), transparent 12%);
  animation: sb-move-bottom var(--sb-speed) linear infinite alternate;
}

.star-border__content {
  position: relative;
  z-index: 1;
  display: block;
  border-radius: 12px;
  background: rgba(10, 14, 13, 0.92);
  padding: 0.75rem 1.5rem;
  text-align: center;
}

@keyframes sb-move-top {
  from { transform: translateX(0); }
  to { transform: translateX(50%); }
}

@keyframes sb-move-bottom {
  from { transform: translateX(0); }
  to { transform: translateX(50%); }
}

@media (prefers-reduced-motion: reduce) {
  .star-border__glow {
    animation: none;
    opacity: 0.5;
  }
}
</style>
