<template>
  <span
    class="app-progress"
    :class="[tone, { compact }]"
    role="progressbar"
    :aria-valuemin="0"
    :aria-valuemax="safeMax"
    :aria-valuenow="safeValue"
  >
    <i :style="{ width: `${percent}%` }"></i>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  value: number;
  max?: number;
  tone?: "primary" | "success" | "warning" | "danger" | "ai";
  compact?: boolean;
}>(), {
  max: 100,
  tone: "primary",
  compact: false
});

const safeMax = computed(() => Math.max(1, Number(props.max) || 100));
const safeValue = computed(() => Math.min(safeMax.value, Math.max(0, Number(props.value) || 0)));
const percent = computed(() => Math.round((safeValue.value / safeMax.value) * 10000) / 100);
</script>

<style scoped>
.app-progress {
  position: relative;
  display: block;
  width: 100%;
  height: 7px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.04);
}
.app-progress.compact {
  height: 5px;
}
.app-progress i {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
  background: var(--color-primary-600);
  transition: width var(--duration-base) var(--ease-in-out), background var(--duration-fast) var(--ease-out);
}
.app-progress.success i {
  background: var(--color-success-500);
}
.app-progress.warning i {
  background: var(--color-warning-500);
}
.app-progress.danger i {
  background: var(--color-danger-500);
}
.app-progress.ai i {
  background: var(--color-ai-gradient);
}
</style>
